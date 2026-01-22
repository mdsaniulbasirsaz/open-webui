<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	const dateRanges = [
		{ label: 'Last 7 days', active: false },
		{ label: 'Last 30 days', active: true },
		{ label: 'Last 90 days', active: false }
	];

	const kpis = [
		{
			title: 'MRR',
			value: '$124.8k',
			change: '12.4%',
			trend: 'up',
			tone: 'positive',
			note: 'vs last 30 days'
		},
		{
			title: 'ARR',
			value: '$1.50m',
			change: '9.1%',
			trend: 'up',
			tone: 'positive',
			note: 'annualized run rate'
		},
		{
			title: 'Active subscriptions',
			value: '3,482',
			change: '3.2%',
			trend: 'up',
			tone: 'positive',
			note: 'net new subscriptions'
		},
		{
			title: 'Churn',
			value: '2.6%',
			change: '0.4%',
			trend: 'down',
			tone: 'positive',
			note: 'logo churn rate'
		},
		{
			title: 'ARPU',
			value: '$35.80',
			change: '1.2%',
			trend: 'up',
			tone: 'positive',
			note: 'avg revenue per user'
		}
	];

	const chartCards = [
		{
			title: 'Revenue trend',
			description: 'Subscription revenue over time',
			metric: '$124.8k',
			change: '12.4%',
			trend: 'up',
			tone: 'positive',
			footnote: 'net new $13.7k'
		},
		{
			title: 'Plan mix',
			description: 'Active subscriptions by plan',
			metric: '3,482',
			change: '3.2%',
			trend: 'up',
			tone: 'positive',
			footnote: 'Plus leads at 41%'
		}
	];

	const planRows = [
		{ name: 'Free', price: '$0', period: '/mo', subs: '1,220', revenue: '$0', conversion: '4.1%' },
		{ name: 'Plus', price: '$20', period: '/mo', subs: '1,420', revenue: '$28.4k', conversion: '38%' },
		{ name: 'Pro', price: '$200', period: '/mo', subs: '310', revenue: '$62.0k', conversion: '9.7%' }
	];

	const invoiceRows = [
		{
			id: 'INV-2026-0412',
			customer: 'Nimbus Labs',
			amount: '$2,450',
			status: 'active',
			issued: 'Jan 12, 2026'
		},
		{
			id: 'INV-2026-0409',
			customer: 'Silverline Studio',
			amount: '$980',
			status: 'trialing',
			issued: 'Jan 9, 2026'
		},
		{
			id: 'INV-2026-0401',
			customer: 'Atlas Ventures',
			amount: '$3,120',
			status: 'past_due',
			issued: 'Jan 1, 2026'
		},
		{
			id: 'INV-2025-0394',
			customer: 'Banyan Health',
			amount: '$1,760',
			status: 'canceled',
			issued: 'Dec 28, 2025'
		}
	];

	const customerRows = [
		{
			name: 'Amina Rahman',
			email: 'amina@horizon.ai',
			role: 'admin',
			plan: 'Plus',
			status: 'active',
			created: 'Sep 3, 2025',
			lastActive: '2 hours ago'
		},
		{
			name: 'Jonas Berg',
			email: 'jonas@silverline.io',
			role: 'user',
			plan: 'Plus',
			status: 'trialing',
			created: 'Nov 19, 2025',
			lastActive: '1 day ago'
		},
		{
			name: 'Rina Patel',
			email: 'rina@atlas.vc',
			role: 'user',
			plan: 'Pro',
			status: 'past_due',
			created: 'Aug 14, 2025',
			lastActive: '4 days ago'
		},
		{
			name: 'Marcos Silva',
			email: 'marcos@banyanhealth.com',
			role: 'user',
			plan: 'Free',
			status: 'canceled',
			created: 'Jun 2, 2025',
			lastActive: '12 days ago'
		}
	];

	const settingsSections = [
		{
			title: 'Payment provider',
			description: 'Billing provider configuration',
			items: [
				{ label: 'Provider', value: 'bKash' },
				{ label: 'Status', value: 'Connected' },
				{ label: 'Payout schedule', value: 'Weekly' },
				{ label: 'Last sync', value: '2 hours ago' }
			]
		},
		{
			title: 'Taxes and trials',
			description: 'Defaults for new subscriptions',
			items: [
				{ label: 'Currency', value: 'USD' },
				{ label: 'Tax rate', value: '7.5%' },
				{ label: 'Trial length', value: '14 days' },
				{ label: 'Invoice footer', value: 'Synapse Labs' }
			]
		}
	];

	const statusStyles = {
		active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		trialing: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-200',
		past_due: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
		canceled: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200'
	};

	const statusLabels = {
		active: 'Active',
		trialing: 'Trialing',
		past_due: 'Past due',
		canceled: 'Canceled'
	};

	const getStatusClass = (status: string) =>
		statusStyles[status] ??
		'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200';

	const getStatusLabel = (status: string) => statusLabels[status] ?? status;
</script>

<div class="flex flex-col gap-6 pb-6">
	<header
		class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
	>
		<div class="mb-4 h-1 w-16 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
		<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
			<div class="space-y-2">
				<h1 class="text-xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Payment Dashboard')}
				</h1>
				<div class="space-y-1 text-sm text-gray-500 dark:text-gray-400">
					<p>{$i18n.t('Track subscription health, revenue, and customers at a glance.')}</p>
					<div class="flex items-center gap-2 text-xs">
						<span class="h-2 w-2 rounded-full bg-emerald-500"></span>
						<span>{$i18n.t('Updated 2 hours ago')}</span>
					</div>
				</div>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<div
					class="inline-flex flex-wrap items-center gap-1 rounded-full border border-gray-200 bg-white p-1 text-xs font-semibold dark:border-gray-700 dark:bg-gray-950"
				>
					{#each dateRanges as range}
						<button
							class={`rounded-full px-3 py-1 transition ${
								range.active
									? 'bg-[rgba(146,39,143,1)] text-white shadow-sm'
									: 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'
							}`}
							type="button"
						>
							{$i18n.t(range.label)}
						</button>
					{/each}
				</div>
				<button
					class="inline-flex items-center rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
					type="button"
				>
					{$i18n.t('Export')}
				</button>
				<button
					class="inline-flex items-center rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:opacity-90"
					type="button"
				>
					{$i18n.t('Create invoice')}
				</button>
			</div>
		</div>
	</header>

	<section
		class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
	>
		<div class="mb-4 flex items-center justify-between gap-3">
			<div class="h-1 w-12 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
			<div class="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent dark:from-gray-800"></div>
		</div>
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Key metrics')}
			</h2>
			<span class="text-xs text-gray-400">{$i18n.t('UI only')}</span>
		</div>
		<div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
			{#each kpis as kpi}
				<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
					<div class="flex items-center justify-between gap-2">
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t(kpi.title)}
						</div>
						<span
							class={`rounded-full px-2 py-0.5 text-xs font-semibold ${
								kpi.tone === 'positive'
									? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200'
									: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200'
							}`}
						>
							{$i18n.t(kpi.trend === 'up' ? 'Up' : 'Down')} {kpi.change}
						</span>
					</div>
					<div class="mt-3 text-2xl font-semibold text-gray-900 dark:text-white">{kpi.value}</div>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t(kpi.note)}</p>
					<div class="mt-3 h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-800">
						<div class="h-1.5 w-3/5 rounded-full bg-[rgba(146,39,143,1)]"></div>
					</div>
				</article>
			{/each}
		</div>
	</section>

	<section class="grid gap-4 lg:grid-cols-2">
		{#each chartCards as chart}
			<div
				class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
			>
				<div class="mb-4 h-1 w-10 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
				<div class="flex items-start justify-between gap-3">
					<div>
						<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
							{$i18n.t(chart.title)}
						</h2>
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(chart.description)}
						</p>
					</div>
					<span class="text-xs text-gray-400">{$i18n.t('UI only')}</span>
				</div>
				<div class="mt-4 flex items-center justify-between gap-3">
					<div class="text-2xl font-semibold text-gray-900 dark:text-white">{chart.metric}</div>
					<span
						class={`rounded-full px-2 py-0.5 text-xs font-semibold ${
							chart.tone === 'positive'
								? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200'
								: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200'
						}`}
					>
						{$i18n.t(chart.trend === 'up' ? 'Up' : 'Down')} {chart.change}
					</span>
				</div>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t(chart.footnote)}</p>
				<div
					class="mt-4 h-40 rounded-xl border border-dashed border-gray-200 bg-gradient-to-br from-gray-50 via-white to-[rgba(146,39,143,0.04)] dark:border-gray-700 dark:from-gray-950 dark:via-gray-900 dark:to-[rgba(146,39,143,0.08)]"
				></div>
			</div>
		{/each}
	</section>

	<section class="grid gap-4 lg:grid-cols-3">
		<div
			class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900 lg:col-span-2"
		>
			<div class="mb-4 h-1 w-12 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Plans')}
					</h2>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Pricing mix and active subscriptions')}
					</p>
				</div>
				<button
					class="text-xs font-semibold text-[rgba(146,39,143,1)] transition hover:opacity-80"
					type="button"
				>
					{$i18n.t('View pricing')}
				</button>
			</div>
			<div class="relative mt-4 overflow-x-auto">
				<table class="min-w-[520px] w-full text-sm">
					<thead class="text-xs uppercase tracking-wide text-gray-400">
						<tr>
							<th class="pb-3 text-left font-medium">{$i18n.t('Plan')}</th>
							<th class="pb-3 text-left font-medium">{$i18n.t('Price')}</th>
							<th class="pb-3 text-left font-medium">{$i18n.t('Active')}</th>
							<th class="pb-3 text-left font-medium">{$i18n.t('Revenue')}</th>
							<th class="pb-3 text-left font-medium">{$i18n.t('Conversion')}</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
						{#each planRows as plan}
							<tr>
								<td class="py-3 text-gray-900 dark:text-white">
									<span class="font-semibold">{$i18n.t(plan.name)}</span>
								</td>
								<td class="py-3 text-gray-500 dark:text-gray-400">
									{plan.price}
									{#if plan.period}
										<span class="text-xs text-gray-400 dark:text-gray-500">{plan.period}</span>
									{/if}
								</td>
								<td class="py-3 text-gray-900 dark:text-white">{plan.subs}</td>
								<td class="py-3 text-gray-900 dark:text-white">{plan.revenue}</td>
								<td class="py-3 text-gray-500 dark:text-gray-400">{plan.conversion}</td>
							</tr>
						{/each}
					</tbody>
				</table>
				<div
					class="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white via-white/80 to-transparent dark:from-gray-900 dark:via-gray-900/80"
				></div>
			</div>
		</div>

		<div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
			<div class="mb-4 h-1 w-12 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
			<div class="flex items-center justify-between">
				<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Recent invoices')}
				</h2>
				<button
					class="text-xs font-semibold text-[rgba(146,39,143,1)] transition hover:opacity-80"
					type="button"
				>
					{$i18n.t('View all')}
				</button>
			</div>
			<div class="mt-4 divide-y divide-gray-200 text-sm dark:divide-gray-800">
				{#each invoiceRows as invoice}
					<div class="flex items-center justify-between gap-3 py-3">
						<div>
							<div class="font-semibold text-gray-900 dark:text-white">{invoice.id}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{$i18n.t(invoice.customer)} · {invoice.issued}
							</div>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-sm font-semibold text-gray-900 dark:text-white">
								{invoice.amount}
							</span>
							<span class={`rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusClass(invoice.status)}`}>
								{$i18n.t(getStatusLabel(invoice.status))}
							</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<section class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
		<div class="mb-4 h-1 w-12 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Customers')}
				</h2>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Subscription status and recent activity')}
				</p>
			</div>
			<button
				class="text-xs font-semibold text-[rgba(146,39,143,1)] transition hover:opacity-80"
				type="button"
			>
				{$i18n.t('Manage users')}
			</button>
		</div>
		<div class="relative mt-4 overflow-x-auto">
			<table class="min-w-[720px] w-full text-sm">
				<thead class="text-xs uppercase tracking-wide text-gray-400">
					<tr>
						<th class="pb-3 text-left font-medium">{$i18n.t('Customer')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Role')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Plan')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Status')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Created')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Last active')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
					{#each customerRows as customer}
						<tr>
							<td class="py-3">
								<div class="font-semibold text-gray-900 dark:text-white">
									{$i18n.t(customer.name)}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{customer.email}
								</div>
							</td>
							<td class="py-3">
								<span
									class="rounded-full border border-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-600 dark:border-gray-700 dark:text-gray-300"
								>
									{$i18n.t(customer.role)}
								</span>
							</td>
							<td class="py-3 text-gray-900 dark:text-white">{$i18n.t(customer.plan)}</td>
							<td class="py-3">
								<span
									class={`rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusClass(
										customer.status
									)}`}
								>
									{$i18n.t(getStatusLabel(customer.status))}
								</span>
							</td>
							<td class="py-3 text-gray-500 dark:text-gray-400">{customer.created}</td>
							<td class="py-3 text-gray-500 dark:text-gray-400">{customer.lastActive}</td>
						</tr>
					{/each}
				</tbody>
			</table>
			<div
				class="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white via-white/80 to-transparent dark:from-gray-900 dark:via-gray-900/80"
			></div>
		</div>
	</section>

	<section class="grid gap-4 lg:grid-cols-2">
		{#each settingsSections as section}
			<div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
				<div class="mb-4 h-1 w-10 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
				<div class="flex items-center justify-between">
					<div>
						<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
							{$i18n.t(section.title)}
						</h2>
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(section.description)}
						</p>
					</div>
					<span class="text-xs text-gray-400">{$i18n.t('UI only')}</span>
				</div>
				<dl class="mt-4 grid gap-3 text-sm">
					{#each section.items as item}
						<div class="flex items-center justify-between gap-4">
							<dt class="text-gray-500 dark:text-gray-400">{$i18n.t(item.label)}</dt>
							<dd class="font-semibold text-gray-900 dark:text-white">{$i18n.t(item.value)}</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/each}
	</section>
</div>
