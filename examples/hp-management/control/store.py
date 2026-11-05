"""Conditional durable records; no external effects inside a transaction."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import json
import time


class Conflict(ValueError):
    pass


@dataclass(frozen=True)
class Write:
    key: str
    value: dict | None
    expected: int | None


@dataclass(frozen=True)
class Check:
    key: str
    expected: int


class MemoryStore:
    """The same optimistic transaction contract used by DynamoDB, for tests."""
    def __init__(self):
        self.rows = {}

    def get(self, key):
        return deepcopy(self.rows.get(key))

    def transact(self, writes):
        if len({w.key for w in writes}) != len(writes):
            raise ValueError('duplicate_transaction_key')
        for w in writes:
            row = self.rows.get(w.key)
            if (row.get('_version') if row else None) != w.expected:
                raise Conflict('concurrent_change')
        for w in writes:
            if isinstance(w, Check):
                continue
            if w.value is None:
                self.rows.pop(w.key, None)
            else:
                self.rows[w.key] = {**deepcopy(w.value), '_version': (w.expected or 0) + 1}

    def put(self, key, value, expected=None):
        self.transact([Write(key, value, expected)])
        return self.get(key)

    def has_attention(self):
        return any(row.get('status') == 'needs_attention' or row.get('reporting_state') == 'needs_attention'
                   for row in self.rows.values())

    def pending(self, limit=25, now=None):
        now = time.time() if now is None else now
        rows = [(k, deepcopy(v)) for k, v in self.rows.items()
                if v.get('queue_state') == 'pending' and v.get('retry_at', 0) <= now]
        return sorted(rows, key=lambda row: row[1].get('retry_at', row[1].get('created_at', 0)))[:limit]


class DynamoStore:
    def __init__(self, table_name, client=None):
        if client is None:
            import boto3
            client = boto3.client('dynamodb')
        self.client, self.table = client, table_name

    @staticmethod
    def _item(key, value, version):
        result = {'pk': {'S': key}, 'body': {'S': json.dumps(value, ensure_ascii=False, separators=(',', ':'))},
                  'version': {'N': str(version)}}
        # Confirmation expiry limits new approval; it must not delete the audit
        # a returning client needs to reconcile or atomically withdraw a lost reply.
        retained_confirmation = key.startswith('approval:')
        if value.get('expires_at') is not None and not retained_confirmation:
            result['expires_at'] = {'N': str(int(value['expires_at']))}
        if value.get('status') == 'needs_attention' or value.get('reporting_state') == 'needs_attention':
            result['attention_state'] = {'S': 'required'}
        if value.get('queue_state'):
            result['queue_state'] = {'S': value['queue_state']}
            result['queue_ready_at'] = {'N': str(int(value.get('retry_at', value.get('created_at', 0))))}
        return result

    def get(self, key):
        item = self.client.get_item(TableName=self.table, Key={'pk': {'S': key}}, ConsistentRead=True).get('Item')
        if not item:
            return None
        return {**json.loads(item['body']['S']), '_version': int(item['version']['N'])}

    def transact(self, writes):
        if not writes or len(writes) > 25 or len({w.key for w in writes}) != len(writes):
            raise ValueError('invalid_transaction')
        items = []
        for w in writes:
            condition = {'ConditionExpression': 'attribute_not_exists(pk)'} if w.expected is None else {
                'ConditionExpression': '#version = :version', 'ExpressionAttributeNames': {'#version': 'version'},
                'ExpressionAttributeValues': {':version': {'N': str(w.expected)}}}
            if isinstance(w, Check):
                items.append({'ConditionCheck': {'TableName': self.table, 'Key': {'pk': {'S': w.key}}, **condition}})
            elif w.value is None:
                items.append({'Delete': {'TableName': self.table, 'Key': {'pk': {'S': w.key}}, **condition}})
            else:
                value = {k: v for k, v in w.value.items() if k != '_version'}
                items.append({'Put': {'TableName': self.table,
                    'Item': self._item(w.key, value, (w.expected or 0) + 1), **condition}})
        try:
            self.client.transact_write_items(TransactItems=items)
        except self.client.exceptions.TransactionCanceledException as exc:
            if any(r.get('Code') == 'ConditionalCheckFailed' for r in exc.response.get('CancellationReasons', [])):
                raise Conflict('concurrent_change') from None
            raise

    def put(self, key, value, expected=None):
        self.transact([Write(key, value, expected)])
        return self.get(key)

    def has_attention(self):
        # Presence is enough; avoid scans, bodies and unbounded counts. GSI
        # eventual consistency may briefly retain an alert after reconciliation.
        response = self.client.query(TableName=self.table, IndexName='attention-state',
            KeyConditionExpression='attention_state = :required',
            ExpressionAttributeValues={':required': {'S': 'required'}}, Select='COUNT', Limit=1)
        return response.get('Count', 0) > 0

    def pending(self, limit=25, now=None):
        now = time.time() if now is None else now
        response = self.client.query(TableName=self.table, IndexName='queue-state',
            KeyConditionExpression='queue_state = :state AND queue_ready_at <= :now',
            ExpressionAttributeValues={':state': {'S': 'pending'}, ':now': {'N': str(int(now))}}, Limit=limit)
        return [(v['pk']['S'], {**json.loads(v['body']['S']), '_version': int(v['version']['N'])})
                for v in response.get('Items', [])]
