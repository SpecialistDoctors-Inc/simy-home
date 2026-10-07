"""Generate all manga homepages from the reviewed Japanese source."""
import json,re
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parents[1]
EXTRA=json.loads((ROOT/'scripts/home-manga-preview-locales.json').read_text())
def render(locale, Localize, content):
    reverse={value:key for key,value in content['copy']['ja'].items()}
    class MangaLocalize(Localize):
        def translate(self,value):
            core=value.strip()
            if not core:return value
            if locale=='ja':target=core
            else:target=EXTRA[locale].get(core,content['copy'][locale].get(reverse.get(core,core),reverse.get(core,core)))
            return value.replace(core,target,1)
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='meta' and attrs.get('property',attrs.get('name')) in ('og:image','twitter:image'):
                suffix='' if locale=='ja' else '-'+locale
                attrs['content']='https://simy.one/assets/home-manga-preview/hero'+suffix+'.webp'
            if tag=='meta' and attrs.get('property') in ('og:image:width','og:image:height'):
                attrs['content']='1672' if attrs['property'].endswith('width') else '941'
            if tag=='img' and '/assets/home-manga-preview/'  in attrs.get('src','') and locale!='ja':
                attrs['src']=attrs['src'].replace('product-ja-v2','product').replace('.webp',f'-{locale}.webp')
            if tag=='script' and attrs.get('src','').startswith('/home-manga-preview.js'):
                attrs['src']=f'/home-manga-{locale}.js?v=1'
            # Japanese source links must follow the generated locale.
            if tag=='a' and attrs.get('href','').startswith('/ja.html'):
                attrs['href']=attrs['href'].replace('/ja.html','/' if locale=='en' else f'/{locale}.html',1)
            if 'data-company-overview' in attrs:
                attrs['href']='https://www.awak.app/#company'
            def order(item):
                key=item[0]
                return (0 if key=='class' else 1 if key=='scope' else 2 if key.startswith('data-') else 3 if key=='href' else 4,key)
            ordered=[(key,None if value=='' else value) for key,value in sorted(attrs.items(),key=order)]
            super().handle_starttag(tag,ordered)
    p=MangaLocalize(locale)
    p.feed((ROOT/'scripts/home-ja-manga.html').read_text())
    return ''.join(p.output)
def demo(locale,content):
    reverse={v:k for k,v in content['copy']['ja'].items()}
    src=(ROOT/'site/home-manga-preview.js').read_text()
    def replace(m):
        t=m.group(1)
        if locale=='ja' or t in ('Done', 'Waiting', 'Next', 'Ready'):return m.group(0)
        target=EXTRA[locale].get(t,content['copy'][locale].get(reverse.get(t,t),reverse.get(t,t)))
        return json.dumps(target,ensure_ascii=False)
    return re.sub(r"'([^'\n]*)'",replace,src)

HEADER_KEYS=['Solutions','Resources','Overview','Apps & integrations','Download','For your work','For engineers','For financial planners','Use cases','Guides','Compare','News','About SIMY','Security','Contact','Legal & service information','Seller information','Android availability']
HEADER_COPY={
'ja':['活用シーン','ガイド・情報','概要','アプリ連携','ダウンロード','職業別の活用','エンジニア向け','ファイナンシャルプランナー向け','活用例','ガイド','比較','ニュース','SIMYについて','セキュリティ','お問い合わせ','法務・サービス情報','販売者情報','Android対応状況'],
'es':['Soluciones','Recursos','Resumen','Aplicaciones e integraciones','Descargar','Para tu trabajo','Para ingenieros','Para asesores financieros','Casos de uso','Guías','Comparar','Noticias','Acerca de SIMY','Seguridad','Contacto','Información legal y del servicio','Información del vendedor','Disponibilidad en Android'],
'fr':['Solutions','Ressources','Présentation','Applications et intégrations','Télécharger','Pour votre métier','Pour les ingénieurs','Pour les conseillers financiers','Cas d’usage','Guides','Comparer','Actualités','À propos de SIMY','Sécurité','Contact','Informations juridiques et du service','Informations sur le vendeur','Disponibilité Android'],
'hi':['समाधान','संसाधन','परिचय','ऐप और एकीकरण','डाउनलोड','आपके काम के लिए','इंजीनियरों के लिए','वित्तीय सलाहकारों के लिए','उपयोग के उदाहरण','गाइड','तुलना','समाचार','SIMY के बारे में','सुरक्षा','संपर्क','कानूनी और सेवा जानकारी','विक्रेता जानकारी','Android उपलब्धता'],
'zh-Hans':['解决方案','资源','概览','应用与集成','下载','适合你的工作','面向工程师','面向理财规划师','使用场景','指南','比较','资讯','关于SIMY','安全','联系我们','法律与服务信息','销售方信息','Android可用情况']}
HEADER_ACCESS = {
'ja':['メニュー','主なナビゲーション','モバイルアプリ','App Storeからダウンロード'],
'es':['Menú','Navegación principal','Aplicaciones móviles','Descargar en App Store'],
'fr':['Menu','Navigation principale','Applications mobiles','Télécharger sur l’App Store'],
'hi':['मेन्यू','मुख्य नेविगेशन','मोबाइल ऐप','App Store से डाउनलोड करें'],
'zh-Hans':['菜单','主导航','移动应用','从App Store下载']}
HEADER_KEYS += ['Navigation menu','Primary navigation','Mobile apps','Download on the App Store']
for language,labels in HEADER_ACCESS.items(): HEADER_COPY[language] += labels
HEADER_SHORT={'hi': {'Sign up':'साइन अप'}}
def localized_header(source,locale,content):
    source=source.replace('site-header.js?v=20261006-compact-1','site-header.js?v=20261008-locale-1')
    if locale=='en':return source
    from html.parser import HTMLParser
    class HeaderText(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.out=[]
        def handle_starttag(self,tag,attrs):
            copy={**content['copy'][locale],**dict(zip(HEADER_KEYS,HEADER_COPY[locale])),**HEADER_SHORT.get(locale,{})}
            attrs=[(key,(copy.get('Language','Language')+value[len('Language'):])
                if key=='aria-label' and value and value.startswith('Language:')
                else copy.get(value,value) if key in ('aria-label','alt','title') else value) for key,value in attrs]
            self.out.append('<'+tag+''.join(' '+key+('' if value is None else '="'+escape(value,quote=True)+'"') for key,value in attrs)+'>')
        def handle_startendtag(self,tag,attrs):
            self.handle_starttag(tag,attrs)
            if tag not in ('img','br','input','meta','link','hr','source','wbr'):
                self.handle_endtag(tag)
        def handle_endtag(self,tag):self.out.append(f'</{tag}>')
        def handle_data(self,data):
            core=data.strip();copy={**content['copy'][locale],**dict(zip(HEADER_KEYS,HEADER_COPY[locale])),**HEADER_SHORT.get(locale,{})}
            self.out.append(escape(data.replace(core,copy.get(core,core),1),quote=False) if core else data)
        def handle_entityref(self,name):self.out.append('&'+name+';')
        def handle_charref(self,name):self.out.append('&#'+name+';')
    m=re.search(r'<header class="simy-header"[\s\S]*?</header>',source)
    if not m:return source
    p=HeaderText();p.feed(m.group())
    return source[:m.start()]+''.join(p.out)+source[m.end():]
