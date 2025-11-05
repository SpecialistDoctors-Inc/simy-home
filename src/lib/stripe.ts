import Stripe from 'stripe';

// Initialize Stripe with the secret key
// Make sure to set STRIPE_SECRET_KEY in your environment variables
export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-10-29.clover',
  typescript: true,
});

/**
 * Create or retrieve a Stripe customer for a user
 */
export async function getOrCreateStripeCustomer(
  userId: string,
  email: string,
  existingCustomerId?: string
): Promise<string> {
  // If customer ID exists, verify it's still valid
  if (existingCustomerId) {
    try {
      await stripe.customers.retrieve(existingCustomerId);
      return existingCustomerId;
    } catch (error) {
      console.error('Invalid customer ID, creating new customer:', error);
    }
  }

  // Create a new customer
  const customer = await stripe.customers.create({
    email,
    metadata: {
      supabase_user_id: userId,
    },
  });

  return customer.id;
}

/**
 * Create a billing portal session for a customer
 */
export async function createBillingPortalSession(
  customerId: string,
  returnUrl: string
): Promise<string> {
  const session = await stripe.billingPortal.sessions.create({
    customer: customerId,
    return_url: returnUrl,
  });

  return session.url;
}
