<script lang="ts">
  import { getContext } from 'svelte';

  const i18n = getContext('i18n');

  type ViewState = 'loaded' | 'loading' | 'empty';
  type PlanStatus = 'Active' | 'Expired' | 'Cancelled';
  type PaymentStatus = 'Paid' | 'Failed' | 'Pending';
  type ActionVariant = 'primary' | 'secondary';

  const viewState: ViewState = 'loaded'; // Can be 'loading' or 'empty' for testing
  const isLoading = viewState === 'loading';
  const hasSubscription = viewState === 'loaded';

  const subscription = {
    plan_name: 'Pro',
    tier: 'Premium',
    billing_cycle: 'Yearly',
    status: 'Active' as PlanStatus,
    start_date: '2025-03-12',
    renewal_date: '2026-03-12',
    expiry_date: '2026-03-12'
  };

  const paymentSummary = {
    amount: 9900,
    tax: 0,
    discount: 1000,
    total: 8900,
    currency: 'BDT',
    payment_status: 'Paid' as PaymentStatus
  };

  const transaction = {
    payment_method: 'BKash',
    transaction_id: 'TXN-92F3A2',
    invoice_id: 'INV-2026-0001',
    paid_date: '2025-03-12'
  };

  const downloads = {
    voucher_url: '/billing/voucher/INV-2026-0001',
    invoice_url: '/billing/invoice/INV-2026-0001'
  };

  const history = [
    {
      paid_date: '2025-03-12',
      amount: 8900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0001'
    },
    {
      paid_date: '2025-02-12',
      amount: 8900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0000'
    },
    {
      paid_date: '2025-02-12',
      amount: 2900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0000'
    },
    {
      paid_date: '2025-02-12',
      amount: 3900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0000'
    },
    {
      paid_date: '2025-02-12',
      amount: 5900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0000'
    },
    {
      paid_date: '2025-02-12',
      amount: 900,
      status: 'Paid' as PaymentStatus,
      invoice_id: 'INV-2026-0000'
    }
  ];

	const activityHistory = [
		{
			activity_type: 'Plan Upgrade',
			activity_date: '2025-02-15',
			status: 'Completed',
			activity_id: 'ACT-2025-001'
		},
		{
			activity_type: 'Payment Issue',
			activity_date: '2025-01-30',
			status: 'Resolved',
			activity_id: 'ACT-2025-002'
		},
		{
			activity_type: 'Subscription Cancellation',
			activity_date: '2025-01-10',
			status: 'Cancelled',
			activity_id: 'ACT-2025-003'
		}
	];


  
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

  // Predefine a set of subtle colors for activity rows
  const activityBgColors = [
    'bg-blue-50 dark:bg-blue-900',
    'bg-amber-50 dark:bg-amber-900',
    'bg-green-50 dark:bg-green-900',
    'bg-purple-50 dark:bg-purple-900',
    'bg-pink-50 dark:bg-pink-900',
    'bg-indigo-50 dark:bg-indigo-900'
  ];

  // Function to pick a random color from the array
  function getRandomBgColor(index: number) {
    // Optional: deterministic random based on index for consistent color
    return activityBgColors[index % activityBgColors.length];
  }


  const numberFormatter = new Intl.NumberFormat('en-US');
  const dateFormatter = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC'
  });

  const formatDate = (value: string) => {
    if (!value) {
      return '-';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return dateFormatter.format(date);
  };

  const formatCurrency = (value: number, currency = paymentSummary.currency) =>
    `${currency} ${numberFormatter.format(value)}`;

  const planDetails = [
    { label: 'Billing cycle', value: subscription.billing_cycle, translate: true },
    { label: 'Start date', value: subscription.start_date, format: 'date' },
    { label: 'Renewal date', value: subscription.renewal_date, format: 'date' },
    { label: 'Expiry date', value: subscription.expiry_date, format: 'date' }
  ];

	const summaryCards = [
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



  const transactionDetails = [
    { label: 'Payment method', value: transaction.payment_method },
    { label: 'Paid date', value: transaction.paid_date, format: 'date' },
    { label: 'Transaction ID', value: transaction.transaction_id },
    { label: 'Invoice/Voucher ID', value: transaction.invoice_id }
  ];

  const actionClasses: Record<ActionVariant, string> = {
    primary:
      'inline-flex items-center rounded-full bg-black px-4 py-2 text-xs font-semibold text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100',
    secondary:
      'inline-flex items-center rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200'
  };

  const actionButtons = [
    { label: 'Download Voucher (PDF)', href: downloads.voucher_url, variant: 'primary' as ActionVariant },
    { label: 'Download Invoice', href: downloads.invoice_url, variant: 'secondary' as ActionVariant }
  ].filter((action) => action.href);

  const planCta = { label: 'Manage Plan', href: '/pricing' };

  const cardClasses =
    'rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900';
  const skeletonLine = 'rounded-full bg-gray-200 dark:bg-gray-800';
  const skeletonRows = Array.from({ length: 4 });
  const skeletonCards = Array.from({ length: 4 });
  const skeletonActions = Array.from({ length: 2 });
  const skeletonHistory = Array.from({ length: 3 });

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
				{#each actionButtons as action}
				<a
					href={action.href}
					class={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors duration-200
					${action.variant === 'primary' && 'bg-green-600 text-white hover:bg-green-700'}
					${action.variant === 'secondary' && 'bg-gray-100 text-gray-800 hover:bg-gray-200'}
					${action.variant === 'destructive' && 'bg-red-600 text-white hover:bg-red-700'}
					${action.variant === 'warning' && 'bg-amber-500 text-white hover:bg-amber-600'}
					`}
				>
					{$i18n.t(action.label)}
				</a>
				{/each}
			</div>
		</section>


		

	<!-- Account Activity Section -->
	<section class={cardClasses}>
		<!-- Section Header -->
		<div class="flex items-center justify-between py-4 border-b border-gray-200 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Account Activity')}
			</div>
			<span class="text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Recent changes and updates')}
			</span>
		</div>

		<!-- Activity List -->
		<div class="mt-4 space-y-4">
			{#each activityHistory as item, index}
			<div class={`flex items-start justify-between gap-4 py-4 px-6 rounded-lg transition-all hover:scale-102 ${getRandomBgColor(index)}`}>
				<!-- Activity Details -->
				<div class="flex-1">
				<div class="flex items-center space-x-2">
					<div class="text-sm font-semibold text-gray-900 dark:text-white">
					{$i18n.t(item.activity_type)}
					</div>
					<span class={`text-xs px-2.5 py-1 rounded-full font-semibold ${getStatusClass(item.status)}`}>
					{$i18n.t(item.status)}
					</span>
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{formatDate(item.activity_date)}
				</div>
				</div>

				<!-- Download Report Button -->
				<div class="flex items-center">
				<a
					href={`/activity/report/${item.activity_id}`}
					class="inline-flex items-center gap-2 py-2 px-4 rounded-full bg-green-600 text-white text-xs font-semibold transition-transform transform hover:scale-105 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 dark:bg-green-500 dark:hover:bg-green-600 dark:focus:ring-green-400"
				>
					{$i18n.t('Download')}
				</a>
				</div>
			</div>
			{/each}
		</div>
	</section>



	{#if history.length}
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

					<!-- Download Button -->
					<a
					href={`/billing/invoice/${item.invoice_id}`}
					class="inline-flex items-center rounded-full px-3 py-2 text-xs font-semibold text-white transition transform hover:scale-105 hover:bg-purple-700"
					style="background-color: rgba(64, 2, 104, 1);"
					>
					{$i18n.t('Download Invoice')}
					</a>
				</div>
				{/each}
			</div>
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
				<!-- Free Plan -->
				<tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900 transition-all">
				<td class="px-4 py-3 font-medium text-gray-900 dark:text-white">Free</td>
				<td class="px-4 py-3 text-gray-700 dark:text-gray-300">Basic Features</td>
				<td class="px-4 py-3 text-gray-900 dark:text-white">{$i18n.t('$0/month')}</td>
				<td class="px-4 py-3 text-center">
					<button class="px-4 py-2 text-xs font-semibold text-white bg-blue-500 rounded-full hover:bg-blue-600 transition-colors">
					{$i18n.t('Select')}
					</button>
				</td>
				</tr>

				<!-- Pro Plan -->
				<tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900 transition-all">
				<td class="px-4 py-3 font-medium text-gray-900 dark:text-white">Pro</td>
				<td class="px-4 py-3 text-gray-700 dark:text-gray-300">Advanced Features</td>
				<td class="px-4 py-3 text-gray-900 dark:text-white">{$i18n.t('$99/month')}</td>
				<td class="px-4 py-3 text-center">
					<button class="px-4 py-2 text-xs font-semibold text-white bg-green-500 rounded-full hover:bg-green-600 transition-colors">
					{$i18n.t('Select')}
					</button>
				</td>
				</tr>
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
