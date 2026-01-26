<script lang="ts">
  import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getMySubscriptionDetails,
		listMyPaymentTransactions,
		listPricingPlans,
		type MySubscriptionDetails,
		type PricingPlan
	} from '$lib/apis/payments';
	import { pricingPlans } from '$lib/data/pricing';
	import Pagination from '$lib/components/common/Pagination.svelte';

  const i18n = getContext('i18n');

  type ViewState = 'loaded' | 'loading' | 'empty';
  type PlanStatus = 'Active' | 'Expired' | 'Cancelled';
  type PaymentStatus = 'Paid' | 'Failed' | 'Pending';

	type PaymentTransaction = {
		id: string;
		user_id: string;
		plan_id?: string | null;
		amount?: number | null;
		currency?: string | null;
		status?: string | null;
		payment_id?: string | null;
		trx_id?: string | null;
		merchant_invoice_number?: string | null;
		raw_response?: Record<string, unknown> | null;
		created_at: number;
		updated_at: number;
	};

  let viewState: ViewState = 'loading';
  let isLoading = true;
  let hasSubscription = false;

	let transactions: PaymentTransaction[] = [];

  let subscription = {
    plan_name: '-',
    tier: '-',
    billing_cycle: '-',
    status: 'Active' as PlanStatus,
    start_date: '',
    renewal_date: '',
    expiry_date: ''
  };

  let paymentSummary = {
    amount: 0,
    tax: 0,
    discount: 0,
    total: 0,
    currency: 'BDT',
    payment_status: 'Pending' as PaymentStatus
  };

  let transaction = {
    payment_method: 'bKash',
    transaction_id: '-',
    invoice_id: '-',
    paid_date: ''
  };

  let downloads = {
    voucher_url: ''
  };

	let history: { paid_date: string; amount: number; status: PaymentStatus; invoice_id: string }[] = [];
	let historyTotal = 0;
	let historyPage = 1;
	let historyPageSize = 5;
	let historyLoading = false;
	let historyLastFetchedPage = 0;

	let comparePlans: PricingPlan[] = [];

  // Calculate the percentage of the subscription progress
	const calculateProgress = (startDate: string, endDate: string): number => {
	const start = new Date(startDate).getTime();
	const end = new Date(endDate).getTime();
	const now = new Date().getTime();

	if (now < start) {
		return 0; // Subscription hasn't started yet
	} else if (now > end) {
		return 100; // Subscription expired
	}

	// Calculate the percentage of time passed
	const progress = ((now - start) / (end - start)) * 100;
	return Math.min(progress, 100); // Ensure it doesn't exceed 100%
	};

  const numberFormatter = new Intl.NumberFormat('en-US');
  const dateFormatter = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC'
  });

  const formatDate = (value: string | number | null | undefined) => {
		if (value === null || value === undefined || value === '') return '-';

		if (typeof value === 'number') {
			const date = new Date(value < 1e12 ? value * 1000 : value);
			return Number.isNaN(date.getTime()) ? '-' : dateFormatter.format(date);
		}

		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return value;
		return dateFormatter.format(date);
  };

  const formatCurrency = (value: number, currency = paymentSummary.currency) =>
    `${currency} ${numberFormatter.format(value)}`;

	let planDetails: { label: string; value: string; translate?: boolean; format?: 'date' }[] = [];
	$: planDetails = [
		{ label: 'Billing cycle', value: subscription.billing_cycle, translate: true },
		{ label: 'Start date', value: subscription.start_date, format: 'date' },
		{ label: 'Renewal date', value: subscription.renewal_date, format: 'date' },
		{ label: 'Expiry date', value: subscription.expiry_date, format: 'date' }
	];

	let summaryCards: { label: string; value: number; format: 'currency' }[] = [];
	$: summaryCards = [
		{ label: 'Amount', value: paymentSummary.amount, format: 'currency' },
		{ label: 'Tax', value: paymentSummary.tax, format: 'currency' },
		{ label: 'Discount', value: paymentSummary.discount, format: 'currency' },
		{ label: 'Total', value: paymentSummary.total, format: 'currency' }
	];

	const cardBgMap: Record<string, string> = {
		Amount: 'bg-blue-50 border-blue-200 text-blue-900',
		Tax: 'bg-amber-50 border-amber-200 text-amber-900',
		Discount: 'bg-green-50 border-green-200 text-green-900',
		Total: 'bg-purple-50 border-purple-200 text-purple-900'
	};

  let transactionDetails: { label: string; value: string; format?: 'date' }[] = [];
	$: transactionDetails = [
		{ label: 'Payment method', value: transaction.payment_method },
		{ label: 'Paid date', value: transaction.paid_date, format: 'date' },
		{ label: 'Transaction ID', value: transaction.transaction_id },
		{ label: 'Invoice/Voucher ID', value: transaction.invoice_id }
	];

  const planCta = { label: 'Manage Plan', href: '/pricing' };

  const cardClasses =
    'rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900';
  const skeletonLine = 'rounded-full bg-gray-200 dark:bg-gray-800';
  const skeletonRows = Array.from({ length: 4 });
  const skeletonCards = Array.from({ length: 4 });
  const skeletonActions = Array.from({ length: 2 });
  const skeletonHistory = Array.from({ length: 3 });

	const normalizePaymentStatus = (value?: string | null): PaymentStatus => {
		const normalized = (value ?? '').trim().toLowerCase();
		if (normalized === 'completed' || normalized === 'success' || normalized === 'paid') return 'Paid';
		if (normalized === 'failed') return 'Failed';
		return 'Pending';
	};

	const normalizePlanStatus = (value?: string | null): PlanStatus => {
		const normalized = (value ?? '').trim().toLowerCase();
		if (normalized === 'canceled' || normalized === 'cancelled') return 'Cancelled';
		if (normalized === 'expired') return 'Expired';
		return 'Active';
	};


	const safeDateIso = (value?: number | null) => {
		if (!value) return '';
		const date = new Date(value * 1000);
		return Number.isNaN(date.getTime()) ? '' : date.toISOString();
	};

	const refreshFromTransactions = () => {
		const latest = transactions[0];
		if (!latest) {
			history = [];
			return;
		}

		const currency = latest.currency ?? paymentSummary.currency ?? 'BDT';
		const amount = Number(latest.amount ?? 0);
		const invoiceId = latest.merchant_invoice_number ?? latest.id;

		paymentSummary = {
			amount,
			tax: 0,
			discount: 0,
			total: amount,
			currency,
			payment_status: normalizePaymentStatus(latest.status)
		};

		transaction = {
			payment_method: 'bKash',
			transaction_id: latest.trx_id ?? latest.payment_id ?? '-',
			invoice_id: invoiceId,
			paid_date: safeDateIso(latest.updated_at ?? latest.created_at)
		};

        downloads = {
            voucher_url: invoiceId ? `/billing/voucher/${invoiceId}` : ''
        };

		history = transactions.map((t) => {
			const id = t.merchant_invoice_number ?? t.id;
			return {
				paid_date: safeDateIso(t.updated_at ?? t.created_at),
				amount: Number(t.amount ?? 0),
				status: normalizePaymentStatus(t.status),
				invoice_id: id
			};
		});
	};

	const fetchHistoryPage = async (page: number) => {
		historyLoading = true;
		historyLastFetchedPage = page;
		try {
			const res = await listMyPaymentTransactions(localStorage.token, {
				page,
				page_size: historyPageSize
			});

			historyTotal = Number(res?.total ?? 0);
			const data = (res?.data ?? []) as PaymentTransaction[];
			transactions = Array.isArray(data) ? data : [];
			refreshFromTransactions();
		} finally {
			historyLoading = false;
		}
	};

	const refreshSubscriptionFromApi = (details: MySubscriptionDetails) => {
		if (!details?.has_subscription) {
			return;
		}

		const planId = (details.plan_id ?? '').trim().toLowerCase();
		const plan = pricingPlans.find((p) => p.planId === planId);

		subscription = {
			plan_name: plan?.name ?? (planId ? planId.toUpperCase() : '-'),
			tier: plan?.tagline ?? '-',
			billing_cycle: plan?.period ?? '-',
			status: normalizePlanStatus(details.status),
			start_date: safeDateIso(details.start_date ?? null),
			renewal_date: safeDateIso(details.renewal_date ?? null),
			expiry_date: safeDateIso(details.expiry_date ?? null)
		};
	};

	onMount(async () => {
		viewState = 'loading';
		isLoading = true;
		hasSubscription = false;
		try {
			const token = localStorage.token;
			const [subscriptionDetails, plansPayload] = await Promise.all([
				getMySubscriptionDetails(token),
				listPricingPlans().catch(() => null)
			]);

			const plansFromApi = (plansPayload?.data ?? []) as PricingPlan[];
			comparePlans =
				Array.isArray(plansFromApi) && plansFromApi.length
					? plansFromApi
					: pricingPlans
							.filter((p) => ['free', 'pro', 'go', 'plus', 'business'].includes(p.planId))
							.map((p) => ({
								plan_id: p.planId,
								name: p.name,
								features: p.tagline ?? '',
								amount: p.amount,
								currency: p.currency,
								period: p.period
							}));

			const hasSubscriptionApi = Boolean(subscriptionDetails?.has_subscription);
			if (hasSubscriptionApi) {
				refreshSubscriptionFromApi(subscriptionDetails as MySubscriptionDetails);
			}

			viewState = 'loaded';
			isLoading = false;
			await fetchHistoryPage(1);
			hasSubscription = hasSubscriptionApi || transactions.length > 0;

			if (!hasSubscriptionApi && !transactions.length) {
				viewState = 'empty';
				hasSubscription = false;
				return;
			}
		} catch (err) {
			viewState = 'empty';
			isLoading = false;
			hasSubscription = false;
			toast.error(typeof err === 'string' ? err : 'Failed to load payment details.');
		}
	});

	$: if (!isLoading && viewState === 'loaded' && !historyLoading) {
		if (historyPage >= 1 && historyPage !== historyLastFetchedPage) {
			fetchHistoryPage(historyPage).catch((err) => {
				toast.error(typeof err === 'string' ? err : 'Failed to load payment history.');
			});
		}
	}

  const statusStyles = {
    Active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
    Expired: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
    Cancelled: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200',
    Paid: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
    Failed: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200',
    Pending: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200'
  };

  const getStatusClass = (status: string) =>
    statusStyles[status] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200';
</script>

<div class="flex flex-col h-full justify-between text-sm" id="tab-payment-details">
  <div class="overflow-y-scroll max-h-[28rem] md:max-h-full">
    {#if isLoading}
      <!-- Skeleton Loader Code (remains unchanged) -->
    {:else}
      <!-- Notification Section -->
      {#if subscription.status === 'Expired'}
        <div class="bg-red-100 text-red-700 text-sm px-4 py-2 rounded-t-lg shadow-md dark:bg-red-900 dark:text-red-200">
          <strong>{$i18n.t('Your subscription has expired!')}</strong> {$i18n.t('Please renew to continue enjoying our service.')}
        </div>
      {/if}

      {#if paymentSummary.payment_status === 'Failed'}
        <div class="bg-yellow-100 text-yellow-700 text-sm px-4 py-2 rounded-t-lg shadow-md dark:bg-yellow-900 dark:text-yellow-200">
          <strong>{$i18n.t('Payment failed!')}</strong> {$i18n.t('Please update your payment method to proceed.')}
        </div>
      {/if}

      <div class="space-y-4">
        <header class="space-y-1">
          <div class="text-base font-medium">{$i18n.t('Payment Details')}</div>
          <div class="text-xs text-gray-500">{$i18n.t('View your plan and payment history.')}</div>
        </header>

        {#if hasSubscription}
          <!-- Subscription Section -->
          <section class={cardClasses}>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Current plan')}</div>
                <div class="text-lg font-semibold" style="color: #92278f;">
                  {$i18n.t(subscription.plan_name)} <span class="text-xs text-gray-400">- {$i18n.t(subscription.tier)}</span>
                </div>
              </div>
			  

              <div class="flex items-center gap-2">
                <span class={`rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusClass(subscription.status)}`}>
                  {$i18n.t(subscription.status)}
                </span>
                <a class="text-xs font-semibold text-gray-500 transition hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200" href={planCta.href}>
                  {$i18n.t(planCta.label)}
                </a>
              </div>

			  
            </div>

			<!-- Progress bar -->
			<div class="mt-3 space-y-2">
				<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Subscription Progress')}</div>
				<div class="w-full bg-gray-200 rounded-full dark:bg-gray-800">
				<!-- Dynamic Progress Bar -->
				<div class="h-2 rounded-full bg-blue-500 dark:bg-blue-700" style="width: {calculateProgress(subscription.start_date, subscription.expiry_date)}%"></div>
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
				{$i18n.t('Progress:')} {Math.round(calculateProgress(subscription.start_date, subscription.expiry_date))}% ({formatDate(subscription.start_date)} - {formatDate(subscription.expiry_date)})
				</div>
			</div>

            <div class="mt-3 flex gap-2">
			  <p class="text-xs text-gray-500 mt-2">{$i18n.t('Pause or cancel your subscription')}</p>
              <button class="inline-flex items-center rounded-full bg-red-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-700" type="button">
                {$i18n.t('Pause')}
              </button>
              <button class="inline-flex items-center rounded-full bg-gray-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-gray-700" type="button">
                {$i18n.t('Cancel')}
              </button>
            </div>

            <dl class="mt-4 grid gap-3 sm:grid-cols-2">
              {#each planDetails as item}
                <div>
                  <dt class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t(item.label)}</dt>
                  <dd class="text-sm font-semibold text-gray-900 dark:text-white">
                    {#if item.format === 'date'}
                      {formatDate(item.value)}
                    {:else if item.translate}
                      {$i18n.t(item.value)}
                    {:else}
                      {item.value}
                    {/if}
                  </dd>
                </div>
              {/each}
            </dl>
          </section>

          <!-- Payment Summary Section -->
          <section class={cardClasses}>
            <div class="flex items-center justify-between">
              <div class="text-sm font-semibold text-gray-900 dark:text-white">
                {$i18n.t('Payment summary')}
              </div>
              <span class={`rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusClass(paymentSummary.payment_status)}`}>
                {$i18n.t(paymentSummary.payment_status)}
              </span>
            </div>

            <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
				{#each summaryCards as card}
					<div
					class={`rounded-xl p-4 border
						${cardBgMap[card.label] ?? 'bg-gray-100 border-gray-200 text-gray-900'}
						dark:bg-opacity-10 dark:border-opacity-30`}
					>
					<div class="text-xs opacity-70">
						{$i18n.t(card.label)}
					</div>

					<div class="mt-1 text-lg font-semibold">
						{card.format === 'currency'
						? formatCurrency(card.value)
						: card.value}
					</div>
					</div>
				{/each}
			</div>


            <div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
              {$i18n.t('Currency')}: {paymentSummary.currency}
            </div>
          </section>

        <!-- Transaction Details Section -->
		<section class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 transition-shadow hover:shadow-md">
			<!-- Header -->
			<div class="text-sm font-semibold text-gray-900 dark:text-white">
				{$i18n.t('Transaction details')}
			</div>

			<!-- Details List -->
			<dl class="mt-4 grid gap-4 sm:grid-cols-2">
				{#each transactionDetails as item}
				<div
					class={`p-3 rounded-lg border
					${
						item.label === 'Payment method' && 'bg-blue-50 border-blue-200 text-blue-900'
					}
					${
						item.label === 'Paid date' && 'bg-amber-50 border-amber-200 text-amber-900'
					}
					${
						item.label === 'Transaction ID' && 'bg-green-50 border-green-200 text-green-900'
					}
					${
						item.label === 'Invoice/Voucher ID' && 'bg-purple-50 border-purple-200 text-purple-900'
					}
					dark:bg-opacity-10 dark:border-opacity-30`}
				>
					<dt class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t(item.label)}
					</dt>
					<dd class="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
					{item.format === 'date' ? formatDate(item.value) : item.value}
					</dd>
				</div>
				{/each}
			</dl>
		</section>




        <!-- Actions Section -->
		<section class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 transition-shadow hover:shadow-md">
			<!-- Header -->
			<div class="text-sm font-semibold text-gray-900 dark:text-white">
				{$i18n.t('Actions')}
			</div>

            <!-- Buttons -->
            <div class="mt-3 flex flex-wrap gap-3">
				{#if downloads.voucher_url}
					<a
						href={downloads.voucher_url}
						class="px-4 py-2 rounded-lg font-semibold text-sm transition-colors duration-200 bg-green-600 text-white hover:bg-green-700"
					>
						{$i18n.t('Download Voucher (PDF)')}
					</a>
				{/if}

				<!-- Invoice download removed -->
            </div>
        </section>


		

	{#if historyLoading}
		<section class={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 transition-shadow hover:shadow-md`}>
			<div class="text-sm font-semibold text-gray-900 dark:text-white">
				{$i18n.t('Payment history')}
			</div>
			<div class="mt-4 space-y-3">
				{#each skeletonHistory as _}
					<div class="h-12 rounded-lg bg-gray-100 dark:bg-gray-900"></div>
				{/each}
			</div>
		</section>
	{:else if history.length}
		<section class={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 transition-shadow hover:shadow-md`}>
			<!-- Header -->
			<div class="flex items-center justify-between">
				<div class="text-sm font-semibold text-gray-900 dark:text-white">
				{$i18n.t('Payment history')}
				</div>
				<span class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Recent')}
				</span>
			</div>

			<!-- Payment List -->
			<div class="mt-4 divide-y divide-gray-200 dark:divide-gray-800">
				{#each history as item, index}
				<div class={`flex flex-wrap items-center justify-between gap-3 py-3 px-4 rounded-lg transition-all 
					${index % 2 === 0 ? 'bg-gray-50 dark:bg-gray-900' : 'bg-gray-100 dark:bg-gray-800'} 
					hover:bg-gray-100 dark:hover:bg-gray-700`}
				>
					<!-- Payment Info -->
					<div>
					<div class="text-sm font-semibold text-gray-900 dark:text-white">
						{formatCurrency(item.amount)}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{item.invoice_id} - {formatDate(item.paid_date)}
					</div>
					</div>

					<!-- Status Badge -->
					<span class={`rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusClass(item.status)}`}>
					{$i18n.t(item.status)}
					</span>

					<!-- Invoice download removed -->
				</div>
				{/each}
			</div>

			{#if historyTotal > historyPageSize}
				<div class="mt-4 flex justify-end">
					<Pagination bind:page={historyPage} count={historyTotal} perPage={historyPageSize} />
				</div>
			{/if}
			</section>
		{/if}



        <!-- Plan Comparison Table -->
		<section class={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 transition-shadow hover:shadow-md`}>
		<!-- Header -->
		<div class="text-sm font-semibold text-gray-900 dark:text-white mb-4">
			{$i18n.t('Compare Plans')}
		</div>

		<!-- Table -->
		<div class="overflow-x-auto">
			<table class="min-w-full table-auto text-left">
			<thead>
				<tr class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
				<th class="px-4 py-3 text-xs font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Plan')}</th>
				<th class="px-4 py-3 text-xs font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Features')}</th>
				<th class="px-4 py-3 text-xs font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Price')}</th>
				<th class="px-4 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Select')}</th>
				</tr>
			</thead>
			<tbody>
				{#each comparePlans as plan, idx (plan.plan_id)}
					<tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900 transition-all">
						<td class="px-4 py-3 font-medium text-gray-900 dark:text-white">{plan.name}</td>
						<td class="px-4 py-3 text-gray-700 dark:text-gray-300">{plan.features}</td>
						<td class="px-4 py-3 text-gray-900 dark:text-white">
							{plan.currency} {numberFormatter.format(plan.amount)}{plan.period}
						</td>
						<td class="px-4 py-3 text-center">
							<button
								class={`px-4 py-2 text-xs font-semibold text-white rounded-full transition-colors ${
									idx % 2 === 0 ? 'bg-blue-500 hover:bg-blue-600' : 'bg-green-500 hover:bg-green-600'
								}`}
								type="button"
								on:click={() => (window.location.href = planCta.href)}
							>
								{$i18n.t('Select')}
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
			</table>
		</div>
		</section>
        {:else}
          <section class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center dark:border-gray-800 dark:bg-gray-900/40">
            <div class="text-sm font-semibold text-gray-900 dark:text-white">
              {$i18n.t('No plan purchased yet.')}
            </div>
            <div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {$i18n.t('Explore plans to get started with billing.')}
            </div>
            <button
              class="mt-4 inline-flex items-center rounded-full bg-black px-4 py-2 text-xs font-semibold text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
              type="button"
            >
              {$i18n.t('Explore Plans')}
            </button>
          </section>
        {/if}
      </div>
    {/if}
  </div>
</div>
