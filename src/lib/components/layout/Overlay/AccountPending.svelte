<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		createBkashPayment,
		executeBkashPayment,
		queryBkashPayment
	} from '$lib/apis/payments';

	const i18n = getContext('i18n');
	const currentYear = new Date().getFullYear();

	const personalPlans = [
		{
			name: 'Free',
			planId: 'free',
			tagline: 'Intelligence for everyday tasks',
			price: '$0',
			amount: 0,
			currency: 'BDT',
			period: '/ month',
			cta: 'Get Free',
			featured: false,
			note: 'Have an existing plan? See billing help',
			features: [
				'Limited access to flagship model GPT-5.2',
				'Limited messages and uploads',
				'Limited and slower image generation',
				'Limited deep research',
				'Limited memory and context'
			]
		},
		{
			name: 'Go',
			planId: 'go',
			tagline: 'Keep chatting with expanded access',
			price: '$8',
			amount: 8,
			currency: 'BDT',
			period: '/ month',
			cta: 'Get Go',
			featured: false,
			note: 'This plan may include ads. Learn more',
			features: [
				'Everything in Free and:',
				'More access to our flagship model GPT-5.2',
				'More messages',
				'More uploads',
				'More image creation',
				'Longer memory'
			]
		},
		{
			name: 'Plus',
			planId: 'plus',
			tagline: 'Do more with advanced intelligence',
			price: '$20',
			amount: 20,
			currency: 'BDT',
			period: '/ month',
			cta: 'Get Plus',
			featured: true,
			note: '',
			features: [
				'Everything in Go and:',
				'Advanced reasoning models',
				'Expanded messages and uploads',
				'Expanded and faster image creation',
				'Expanded deep research and agent mode',
				'Expanded memory and context',
				'Projects, tasks, and custom GPTs',
				'Codex agent and Sora video generation',
				'Early access to new features'
			]
		},
		{
			name: 'Pro',
			planId: 'pro',
			tagline: 'Full access to the best of ChatGPT',
			price: '$200',
			amount: 200,
			currency: 'BDT',
			period: '/ month',
			cta: 'Get Pro',
			featured: false,
			note: '',
			features: [
				'Everything in Plus and:',
				'Pro reasoning with GPT-5.2 Pro',
				'Unlimited messages and uploads',
				'Unlimited and faster image creation',
				'Maximum deep research and agent mode',
				'Maximum memory and context',
				'Expanded projects, tasks, and custom GPTs',
				'Expanded access to Sora video generation',
				'Expanded, priority-speed Codex agent',
				'Research preview of new features'
			]
		},
		{
			name: 'Business',
			planId: 'business',
			tagline: 'A secure, collaborative workspace for startups and growing businesses',
			price: '$25',
			amount: 25,
			currency: 'BDT',
			period: '/ user / month billed annually',
			cta: 'Try for free',
			featured: false,
			note: '',
			features: [
				'Everything in Plus and:',
				'Unlimited GPT-5.2 messages, with generous access to GPT-5.2 Thinking, and access to GPT-5.2 Pro, plus the flexibility to add credits as needed',
				'60+ apps that bring your tools and data into ChatGPT, like Slack, Google Drive, SharePoint, GitHub, Atlassian, and more',
				'A secure, dedicated workspace with essential admin controls, SAML SSO, and MFA',
				'Support for compliance with GDPR, CCPA, and other privacy laws. Aligned with CSA STAR and SOC 2 Type 2',
				'Business features like apps, data analysis, record mode, canvas, shared projects, and custom workspace GPTs',
				'Encryption at rest and in transit, and no training on your business data by default. Learn more',
				'Includes access to Codex and ChatGPT agent for reasoning and taking action across your documents, tools, and codebases'
			]
		}
	];

	const tokenUsage = [
		'Tokens are used for messages, tool calls, uploads, and image generation.',
		'Each plan includes a monthly token budget that resets every billing cycle.',
		'Higher plans expand token limits and response speed.',
		'Business and Enterprise can add flexible credits for extra usage.',
		'Track remaining tokens and add credits from billing.'
	];

	const comparisonColumns = ['Free', 'Go', 'Plus', 'Pro', 'Business', 'Enterprise'];
	const comparisonCtas = [
		{ label: 'Get Free' },
		{ label: 'Get Go' },
		{ label: 'Get Plus' },
		{ label: 'Get Pro' },
		{ label: 'Get Business' },
		{ label: 'Contact sales' }
	];

	const comparisonGroups = [
		{
			title: 'Essentials',
			rows: [
				{
					feature: 'Messages and interactions',
					values: ['Limited', 'Expanded', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'Chat history',
					values: ['Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'Access on web, iOS, Android',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				}
			]
		},
		{
			title: 'Models',
			rows: [
				{
					feature: 'GPT-5.2 Instant',
					values: ['Yes', 'Expanded', 'Expanded', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'GPT-5.2 Thinking',
					values: ['No', 'No', 'Expanded', 'Unlimited*', 'Flexible**', 'Flexible**']
				},
				{
					feature: 'GPT-5.2 Pro',
					values: ['No', 'No', 'No', 'Yes', 'Flexible**', 'Flexible**']
				},
				{
					feature: 'Legacy models',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				}
			]
		},
		{
			title: 'Response times',
			rows: [
				{
					feature: 'Response times',
					values: [
						'Limited on bandwidth and availability',
						'Limited on bandwidth and availability',
						'Fast',
						'Fast',
						'Fast',
						'Fastest'
					]
				}
			]
		},
		{
			title: 'Context window',
			rows: [{ feature: 'Context window', values: ['16K', '32K', '32K', '128K', '32K', '128K'] }]
		},
		{
			title: 'Regular updates',
			rows: [
				{
					feature: 'Regular quality and speed updates as models improve',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				}
			]
		},
		{
			title: 'Features',
			rows: [
				{
					feature: 'Voice',
					values: ['Yes', 'Expanded', 'Expanded', 'Unlimited*', 'Expanded', 'Flexible**']
				},
				{
					feature: 'Voice with video',
					values: ['No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Memory',
					values: ['Limited', 'Yes', 'Expanded', 'Expanded', 'Expanded', 'Expanded']
				},
				{
					feature: 'Memory with past chats',
					values: ['Limited', 'Yes', 'Expanded', 'Expanded', 'Coming soon', 'Coming soon']
				},
				{
					feature: 'Search',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Canvas',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Code edits on macOS',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Projects',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Shared projects',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Tasks',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Data analysis',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Vision',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps connecting to internal tools',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Interactive apps',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'App directory',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Company knowledge',
					values: ['No', 'No', 'No', 'No', 'Yes', 'Yes']
				},
				{
					feature: 'Developer mode (beta)',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'ChatGPT record mode',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'File uploads',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Discover & use GPTs',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Create & share GPTs',
					values: ['No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Share GPTs with your workspace',
					values: ['No', 'No', 'No', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Opportunities to test new features',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Image generation',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Interactive tables and charts',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Sora 1',
					values: ['No', 'No', 'Limited', 'Expanded', 'Limited', 'No']
				},
				{
					feature: 'Sora 2',
					values: ['Yes', 'Yes', 'Yes', 'Expanded', 'Yes', 'Yes']
				},
				{
					feature: 'Codex agent',
					values: ['No', 'No', 'Yes', 'Expanded', 'Yes', 'Yes']
				},
				{
					feature: 'Deep research',
					values: ['Limited', 'Limited', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps for deep research',
					values: ['Limited', 'Limited', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Study mode',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'ChatGPT Pulse',
					values: ['No', 'No', 'No', 'Yes', 'No', 'No']
				}
			]
		}
	];

	let paymentStatus: 'idle' | 'processing' | 'success' | 'error' | 'canceled' = 'idle';
	let paymentMessage = '';
	let paymentId = '';
	let processingPlanId = '';

	const normalizeStatusValue = (status: string) => status.trim().toLowerCase();

	const isSuccessStatus = (status: string) =>
		['executed', 'confirmed', 'success', 'completed'].includes(normalizeStatusValue(status));

	const isCanceledStatus = (status: string) => {
		const normalized = normalizeStatusValue(status);
		return normalized.includes('cancel') || normalized === 'aborted' || normalized === 'abort';
	};

	const isFailureStatus = (status: string) => {
		const normalized = normalizeStatusValue(status);
		return (
			normalized.includes('fail') ||
			normalized.includes('error') ||
			normalized.includes('reject') ||
			normalized.includes('declin')
		);
	};

	const isPendingStatus = (status: string) => {
		const normalized = normalizeStatusValue(status);
		return (
			normalized.includes('pending') ||
			normalized.includes('created') ||
			normalized.includes('initiated')
		);
	};

	const getStatusBadgeClasses = (status: string) => {
		if (status === 'success') {
			return 'bg-emerald-100 text-emerald-700';
		}
		if (status === 'canceled') {
			return 'bg-rose-100 text-rose-700';
		}
		if (status === 'error') {
			return 'bg-rose-100 text-rose-700';
		}
		return 'bg-amber-100 text-amber-700';
	};

	const getReturnStatus = (searchParams: URLSearchParams) => {
		const rawStatus =
			searchParams.get('status') ||
			searchParams.get('statusMessage') ||
			searchParams.get('message');
		const statusCode = searchParams.get('statusCode');

		if (rawStatus) {
			const normalized = normalizeStatusValue(rawStatus);
			if (isCanceledStatus(normalized)) {
				return 'canceled';
			}
			if (isFailureStatus(normalized)) {
				return 'failed';
			}
			if (isSuccessStatus(normalized)) {
				return 'success';
			}
		}

		if (statusCode) {
			return statusCode === '0000' ? 'success' : 'failed';
		}

		return null;
	};

	const applyPaymentOutcome = (status: string, message?: string) => {
		const normalized = status ? normalizeStatusValue(status) : 'unknown';
		if (isSuccessStatus(normalized)) {
			paymentStatus = 'success';
			paymentMessage = $i18n.t('Payment confirmed. Your plan is now active.');
			return;
		}
		if (isCanceledStatus(normalized)) {
			paymentStatus = 'canceled';
			paymentMessage = message || $i18n.t('Payment was canceled.');
			return;
		}
		if (isPendingStatus(normalized)) {
			paymentStatus = 'processing';
			paymentMessage = $i18n.t('Payment is still pending. Please try again.');
			return;
		}
		if (isFailureStatus(normalized)) {
			paymentStatus = 'error';
			paymentMessage = message || $i18n.t('Payment failed. Please try again.');
			return;
		}
		paymentStatus = 'error';
		paymentMessage = message || $i18n.t('Payment could not be confirmed.');
	};

	const normalizePaymentError = (err: unknown, fallback: string) => {
		if (!err) {
			return fallback;
		}
		if (typeof err === 'string') {
			return err;
		}
		if (typeof err === 'object') {
			const errRecord = err as Record<string, unknown>;
			if (typeof errRecord.detail === 'string') {
				return errRecord.detail;
			}
			if (typeof errRecord.message === 'string') {
				return errRecord.message;
			}
		}
		return fallback;
	};

	const handlePaymentReturn = async (returnedPaymentId: string, returnStatus: string | null) => {
		if (!returnedPaymentId) {
			return;
		}

		if (!localStorage.token) {
			paymentStatus = 'error';
			paymentMessage = $i18n.t('Please sign in to complete payment.');
			return;
		}

		paymentId = returnedPaymentId;

		if (returnStatus === 'canceled') {
			paymentStatus = 'canceled';
			paymentMessage = $i18n.t('Payment was canceled.');
			return;
		}

		paymentStatus = 'processing';
		paymentMessage = $i18n.t('Finalizing your payment...');

		if (returnStatus === 'failed') {
			try {
				const result = await queryBkashPayment(localStorage.token, returnedPaymentId);
				applyPaymentOutcome(result?.status ?? 'unknown');
			} catch (err) {
				paymentStatus = 'error';
				paymentMessage = normalizePaymentError(err, $i18n.t('Payment failed. Please try again.'));
			}
			return;
		}

		try {
			const result = await executeBkashPayment(localStorage.token, {
				payment_id: returnedPaymentId
			});
			applyPaymentOutcome(result?.status ?? 'unknown', result?.message);
		} catch (err) {
			const executeErrorMessage = normalizePaymentError(err, '');
			try {
				const result = await queryBkashPayment(localStorage.token, returnedPaymentId);
				applyPaymentOutcome(result?.status ?? 'unknown', executeErrorMessage);
			} catch (queryError) {
				paymentStatus = 'error';
				paymentMessage =
					executeErrorMessage ||
					normalizePaymentError(queryError, $i18n.t('Unable to verify payment status.'));
			}
		}
	};

	const handleCheckout = async (plan) => {
		if (plan.amount <= 0) {
			toast.success($i18n.t('Free plan selected.'));
			return;
		}

		if (!localStorage.token) {
			toast.error($i18n.t('Please sign in to continue.'));
			return;
		}

		paymentStatus = 'processing';
		paymentMessage = $i18n.t('Redirecting to bKash...');
		processingPlanId = plan.planId;

		try {
			const result = await createBkashPayment(localStorage.token, {
				plan_id: plan.planId,
				amount: plan.amount,
				currency: plan.currency
			});
			const redirectUrl = result?.bkash_url ?? result?.bkashURL;
			paymentId = result?.payment_id ?? '';

			if (redirectUrl) {
				window.location.href = redirectUrl;
				return;
			}

			paymentStatus = 'error';
			paymentMessage = $i18n.t('Unable to start payment.');
			processingPlanId = '';
		} catch (err) {
			const message = normalizePaymentError(err, $i18n.t('Unable to start payment.'));
			paymentStatus = 'error';
			paymentMessage = message;
			processingPlanId = '';
			toast.error(message);
		}
	};

	onMount(() => {
		const searchParams = new URLSearchParams(window.location.search);
		const returnedPaymentId =
			searchParams.get('paymentID') || searchParams.get('payment_id') || '';
		const returnStatus = getReturnStatus(searchParams);
		if (returnedPaymentId) {
			handlePaymentReturn(returnedPaymentId, returnStatus);
		} else if (returnStatus === 'canceled') {
			paymentStatus = 'canceled';
			paymentMessage = $i18n.t('Payment was canceled.');
		}
	});
</script>

<div class="fixed inset-0 z-[999] bg-white text-[#1d1424]">
	<div class="h-full w-full overflow-y-auto">
		<div class="mx-auto w-full max-w-8xl px-4 py-8 sm:px-6 lg:px-8">
			<div
				class="rounded-2xl bg-white p-6 shadow-[0_28px_70px_rgba(22,10,30,0.28)] sm:rounded-[28px] sm:p-10"
			>
				<div class="flex flex-col gap-6">
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-3">
							<img
								src="/static/logo.png"
								alt="Synapse logo"
								class="h-10 w-10 rounded-full border border-[rgba(39,20,46,0.14)] object-contain"
							/>
							<span class="text-2xl font-semibold tracking-[0.12em] text-[rgba(146,39,143,1)]">
								Synapse
							</span>
						</div>
						<button
							class="rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-xs font-semibold text-white whitespace-nowrap"
							type="button"
							on:click={async () => {
								localStorage.removeItem('token');
								location.href = '/auth';
							}}
						>
							{$i18n.t('Sign Out')}
						</button>
					</div>
					<header class="mx-auto max-w-2xl text-center">
						<h1 class="font-serif text-3xl text-[rgba(146,39,143,1)] font-semibold tracking-[0.02em] sm:text-4xl">
							Pricing
						</h1>
						<p class="mt-2 text-sm text-[#5a4b64] sm:text-base">
							See pricing for our individual, business, and enterprise plans.
						</p>
					</header>
				</div>

				<section class="mt-8 grid gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-3">
					{#each personalPlans as plan}
						<article
							class={`flex h-full flex-col gap-4 rounded-2xl border p-4 sm:p-5 ${
								plan.featured
									? 'border-[rgba(146,39,143,1)]'
									: 'border-[rgba(39,20,46,0.14)]'
							}`}
						>
							<div class="flex flex-col gap-2">
								<div class="text-lg font-semibold">{plan.name}</div>
								<div class="text-sm text-[#5a4b64]">{plan.tagline}</div>
								<div class="flex flex-wrap items-baseline gap-2 font-semibold">
									<span class="text-2xl">{plan.price}</span>
									{#if plan.period}
										<span class="text-sm text-[#5a4b64]">{plan.period}</span>
									{/if}
								</div>
								<button
									class="mt-2 w-fit rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(146,39,143,0.3)] transition disabled:cursor-not-allowed disabled:opacity-60"
									type="button"
									disabled={paymentStatus === 'processing' || processingPlanId === plan.planId}
									on:click={() => handleCheckout(plan)}
								>
									{#if processingPlanId === plan.planId}
										{$i18n.t('Processing...')}
									{:else}
										{plan.cta}
									{/if}
								</button>
							</div>
							<ul class="space-y-2 text-sm text-[#5a4b64]">
								{#each plan.features as feature}
									<li class="flex gap-2">
										<span class="mt-[2px] text-[rgba(146,39,143,1)]">&#10004;</span>
										<span>{feature}</span>
									</li>
								{/each}
							</ul>
							{#if plan.note}
								<p class="text-xs text-[#5a4b64]">{plan.note}</p>
							{/if}
						</article>
					{/each}
				</section>

				{#if paymentStatus !== 'idle'}
					<section
						class="mt-8 rounded-2xl border border-[rgba(39,20,46,0.12)] bg-white p-4 sm:p-5"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
							<div class="flex items-center gap-3">
								<span
									class={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusBadgeClasses(
										paymentStatus
									)}`}
								>
									{$i18n.t(
										paymentStatus === 'processing'
											? 'Processing'
											: paymentStatus === 'canceled'
												? 'Canceled'
												: paymentStatus
									)}
								</span>
								<div class="text-sm font-semibold text-[#1d1424]">
									{$i18n.t('Payment status')}
								</div>
							</div>
							{#if paymentId}
								<div class="text-xs text-[#5a4b64]">{$i18n.t('Payment ID')}: {paymentId}</div>
							{/if}
						</div>
						<p class="mt-3 text-sm text-[#5a4b64]">{paymentMessage}</p>
					</section>
				{/if}

				<section class="mt-8 rounded-2xl border border-[rgba(146,39,143,0.12)] bg-[rgba(146,39,143,0.06)] p-4 sm:p-5">
					<h2 class="text-lg font-semibold">Token usage when you purchase a plan</h2>
					<ul class="mt-3 space-y-2 text-sm text-[#5a4b64]">
						{#each tokenUsage as item}
							<li class="flex gap-2">
								<span class="mt-[2px] text-[rgba(146,39,143,1)]">&#10004;</span>
								<span>{item}</span>
							</li>
						{/each}
					</ul>
				</section>

				<section class="mt-8">
					<h2 class="text-lg font-semibold">Compare features across plans</h2>
					<div class="mt-3 flex flex-wrap gap-2">
						{#each comparisonCtas as cta}
							<button
								class="rounded-full border border-[rgba(146,39,143,0.3)] px-3 py-1 text-xs font-semibold text-[rgba(146,39,143,1)] transition hover:bg-[rgba(146,39,143,0.12)] hover:text-[#1d1424]"
								type="button"
							>
								{cta.label}
							</button>
						{/each}
					</div>
					<div class="mt-4 overflow-x-auto rounded-2xl border border-[rgba(39,20,46,0.14)]">
						<table class="min-w-[760px] w-full border-collapse text-sm">
							<thead class="bg-[rgba(146,39,143,0.08)] text-left">
								<tr>
									<th class="px-3 py-3 font-semibold sm:px-4">Feature</th>
									{#each comparisonColumns as column}
										<th class="px-3 py-3 font-semibold sm:px-4">{column}</th>
									{/each}
								</tr>
							</thead>
							{#each comparisonGroups as group}
								<tbody>
									<tr class="bg-[rgba(16,10,24,0.04)]">
										<th
											colspan={comparisonColumns.length + 1}
											class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] sm:px-4"
										>
											{group.title}
										</th>
									</tr>
									{#each group.rows as row}
										<tr class="border-t border-[rgba(39,20,46,0.14)]">
											<th class="px-3 py-3 text-left font-semibold text-[#1d1424] sm:px-4">
												{row.feature}
											</th>
											{#each row.values as value}
												<td class="px-3 py-3 align-top text-[#5a4b64] sm:px-4">{value}</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							{/each}
						</table>
					</div>
				</section>

				<div class="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
					<button
						class="w-fit rounded-full border border-[rgba(39,20,46,0.2)] px-5 py-2 text-sm font-semibold text-[#1d1424]"
						type="button"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{$i18n.t('Check Again')}
					</button>
				</div>

				<footer class="mt-10 border-t border-[rgba(39,20,46,0.14)] pt-6 text-xs text-[#5a4b64]">
					<div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
						<a href="" class="flex items-start gap-3 sm:items-center">
							<img
								src="/static/logo.png"
								alt="Synapse logo"
								class="h-12 w-12 rounded-full border border-[rgba(39,20,46,0.14)] object-contain"
							/>
							<div>
								<div class="text-2xl font-semibold text-[#1d1424]">Synapse</div>
								<div class="text-xs text-[#5a4b64]">Intelligence for teams and creators.</div>
							</div>
						</a>
						<div class="text-left">
							<div class="text-sm font-semibold text-[#1d1424]">Contact</div>
							<div class="mt-2">bdrenai@services.bdren.net.bd</div>
							
						</div>
						<div class="text-left lg:text-right">
							<div class="text-sm font-semibold text-[#1d1424]">Legal</div>
							<div class="mt-2">Privacy | Terms | Security</div>
							<div class="mt-1">Copyright {currentYear} Synapse. All rights reserved.</div>
						</div>
					</div>
				</footer>
			</div>
		</div>
	</div>
</div>
