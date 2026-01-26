export type PricingPlan = {
	name: string;
	planId: string;
	price: string;
	amount: number;
	currency: string;
	period: string;
	tagline?: string;
};

export const pricingPlans: PricingPlan[] = [
	{
		name: 'Free',
		planId: 'free',
		tagline: 'Intelligence for everyday tasks',
		price: 'BDT 0',
		amount: 0,
		currency: 'BDT',
		period: '/ month'
	},
	{
		name: 'Go',
		planId: 'go',
		tagline: 'Keep chatting with expanded access',
		price: 'BDT 999',
		amount: 999,
		currency: 'BDT',
		period: '/ month'
	},
	{
		name: 'Plus',
		planId: 'plus',
		tagline: 'Do more with advanced intelligence',
		price: 'BDT 2420',
		amount: 2420,
		currency: 'BDT',
		period: '/ month'
	},
	{
		name: 'Pro',
		planId: 'pro',
		tagline: 'Full access to the best of ChatGPT',
		price: 'BDT 24270',
		amount: 24270,
		currency: 'BDT',
		period: '/ month'
	},
	{
		name: 'Business',
		planId: 'business',
		tagline: 'A secure, collaborative workspace for startups and growing businesses',
		price: 'BDT 3030',
		amount: 3030,
		currency: 'BDT',
		period: '/ user / month billed annually'
	}
];
