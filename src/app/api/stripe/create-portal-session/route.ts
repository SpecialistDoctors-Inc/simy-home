import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';

export async function POST(request: NextRequest) {
  try {
    // Get authenticated user
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized', details: authError?.message },
        { status: 401 }
      );
    }

    const returnUrl = `${request.nextUrl.origin}/mypage`;

    // Import Stripe utilities
    const { getOrCreateStripeCustomer, createBillingPortalSession } = await import('@/lib/stripe');
    
    // Get existing customer ID from user metadata
    const existingCustomerId = user.user_metadata?.stripe_customer_id;
    
    // Get or create customer
    const customerId = await getOrCreateStripeCustomer(
      user.id,
      user.email!,
      existingCustomerId
    );

    // Save customer ID to user metadata if it's new
    if (customerId !== existingCustomerId) {
      await supabase.auth.updateUser({
        data: { stripe_customer_id: customerId }
      });
    }

    // Create billing portal session
    const portalUrl = await createBillingPortalSession(customerId, returnUrl);

    return NextResponse.json({ url: portalUrl });
  } catch (error) {
    console.error('Error creating portal session:', error);
    return NextResponse.json(
      { error: 'Failed to create portal session' },
      { status: 500 }
    );
  }
}
