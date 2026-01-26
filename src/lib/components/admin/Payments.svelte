<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		adminExportPaymentTransactions,
		adminListPaymentTransactions,
		adminPaymentKpis,
		adminPaymentMetrics,
		adminPaymentPlansSummary,
		adminPlanTotalAmount
	} from '$lib/apis/payments';
	import { getUsers } from '$lib/apis/users';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { pricingPlans } from '$lib/data/pricing';

	const i18n = getContext('i18n');

	const dateRanges = [
		{ label: 'All time', days: null },
		{ label: 'Last 7 days', days: 7 },
		{ label: 'Last 30 days', days: 30 },
		{ label: 'Last 90 days', days: 90 }
	];

	const chartCards = [
		{
			title: 'Revenue trend',
			description: 'Subscription revenue over time',
			metric: '—',
			change: '',
			trend: 'up',
			tone: 'positive',
			footnote: 'net new revenue'
		},
		{
			title: 'Status breakdown',
			description: 'Transactions by status',
			metric: '—',
			change: '',
			trend: 'up',
			tone: 'positive',
			footnote: 'latest filtered results'
		}
	];

	let planRows: {
		name: string;
		price: string;
		period: string;
		subs: string;
		revenue: string;
		conversion: string;
	}[] = [];

	type Customer = {
		id: string;
		name: string;
		email: string;
		role: string;
		created_at?: number | null;
		last_active_at?: number | null;
	};

	let customers: Customer[] = [];
	let customersLoading = false;
	let customersTotals: Record<string, { total_amount: number; currency: string | null }> = {};
	let providerLastSyncAt: number | null = null;

	const markProviderSynced = () => {
		providerLastSyncAt = Math.floor(Date.now() / 1000);
	};

	const settingsSections = [
		{
			title: 'Payment provider',
			description: 'Billing provider configuration',
			items: [
				{ label: 'Provider', value: 'bKash' },
				{ label: 'Status', value: 'Connected' },
				{ label: 'Payout schedule', value: 'Weekly' },
				{ label: 'Last sync', value: '' }
			]
		},
		{
			title: 'Taxes and trials',
			description: 'Defaults for new subscriptions',
			items: [
				{ label: 'Currency', value: 'BDT' },
				{ label: 'Tax rate', value: '' },
				{ label: 'Trial length', value: '' },
				{ label: 'Invoice footer', value: 'Synapse' }
			]
		}
	];

	const statusStyles = {
		active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		trialing: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-200',
		past_due: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
		canceled: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200',
		executed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		confirmed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
		failed: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200',
		pending: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
		created: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-200',
		unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200'
	};

	const statusLabels = {
		active: 'Active',
		trialing: 'Trialing',
		past_due: 'Past due',
		canceled: 'Canceled',
		executed: 'Executed',
		confirmed: 'Confirmed',
		completed: 'Completed',
		success: 'Success',
		failed: 'Failed',
		pending: 'Pending',
		created: 'Created',
		unknown: 'Unknown'
	};

	const getStatusClass = (status: string) =>
		statusStyles[status] ??
		'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200';

	const getStatusLabel = (status: string) => statusLabels[status] ?? status;

	const getUserLabel = (transaction: PaymentTransaction) => {
		if (transaction.user_email) return transaction.user_email;
		if (transaction.user_name) return transaction.user_name;
		if (transaction.username) return transaction.username;
		return transaction.user_id;
	};

	type PaymentTransaction = {
		id: string;
		user_id: string;
		user_email?: string | null;
		user_name?: string | null;
		username?: string | null;
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

	let transactions: PaymentTransaction[] | null = null;
	let transactionsTotal = 0;
	let transactionsPage = 1;
	let transactionsPageSize = 8;
	let transactionsLoading = false;
	let metricsLoading = false;
	let totalMetricsLoading = false;
	let exportLoading = false;
	let metrics = {
		total_amount: 0,
		total_transactions: 0,
		avg_amount: 0,
		currency: null,
		status_breakdown: [] as { status: string; count: number }[],
		revenue_trend: [] as { date: string; amount: number; count: number }[]
	};
	let kpis = {
		mrr: 0,
		arr: 0,
		active_subscriptions: 0,
		arpu: 0,
		churn: null as number | null,
		currency: null as string | null
	};
	let rangeKpisLoading = false;
	let rangeKpis = {
		mrr: 0,
		arr: 0,
		active_subscriptions: 0,
		arpu: 0,
		churn: null as number | null,
		currency: null as string | null
	};
	let statusFilter = '';
	let searchField: 'user_id' | 'payment_id' | 'trx_id' | 'merchant_invoice_number' | 'user_query' =
		'payment_id';
	let searchQuery = '';
	let startDate = '';
	let endDate = '';
	let selectedRange = 'Last 30 days';
	let sortKey: 'created_at' | 'amount' | 'status' = 'created_at';
	let sortDirection: 'asc' | 'desc' = 'desc';
	let plansLoading = false;
	let planSummaries: {
		plan_id: string;
		total_amount: number;
		total_transactions: number;
		currency?: string | null;
	}[] = [];
	let planTotals: Record<
		string,
		{ total_amount: number; total_transactions: number; currency?: string | null }
	> = {};

	const statusOptions = [
		{ value: '', label: 'All statuses' },
		{ value: 'created', label: 'Created' },
		{ value: 'pending', label: 'Pending' },
		{ value: 'executed', label: 'Executed' },
		{ value: 'confirmed', label: 'Confirmed' },
		{ value: 'completed', label: 'Completed' },
		{ value: 'success', label: 'Success' },
		{ value: 'failed', label: 'Failed' },
		{ value: 'canceled', label: 'Canceled' },
		{ value: 'unknown', label: 'Unknown' }
	];

	const numberFormatter = new Intl.NumberFormat('en-US', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});

	const dateFormatter = new Intl.DateTimeFormat('en-US', {
		day: '2-digit',
		month: 'short',
		year: 'numeric'
	});

	const formatAmount = (amount?: number | null, currency?: string | null) => {
		if (amount === null || amount === undefined) return '-';
		const formatted = numberFormatter.format(amount);
		return currency ? `${currency} ${formatted}` : formatted;
	};

	const formatDate = (timestamp?: number | null) => {
		if (!timestamp) return '-';
		const date = new Date(timestamp * 1000);
		if (Number.isNaN(date.getTime())) return '-';
		return dateFormatter.format(date);
	};

	const formatLastActive = (timestamp?: number | null) => {
		if (!timestamp) return '-';
		const diffSeconds = Math.floor(Date.now() / 1000 - timestamp);
		if (diffSeconds < 60) return 'just now';
		if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} min ago`;
		if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} hours ago`;
		return `${Math.floor(diffSeconds / 86400)} days ago`;
	};

	const dateInputFormatter = new Intl.DateTimeFormat('en-CA', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit'
	});

	const formatDateInput = (date: Date) => dateInputFormatter.format(date);

	const toUnixStart = (value: string) => {
		if (!value) return undefined;
		const date = new Date(`${value}T00:00:00`);
		if (Number.isNaN(date.getTime())) return undefined;
		return Math.floor(date.getTime() / 1000);
	};

	const toUnixEnd = (value: string) => {
		if (!value) return undefined;
		const date = new Date(`${value}T23:59:59`);
		if (Number.isNaN(date.getTime())) return undefined;
		return Math.floor(date.getTime() / 1000);
	};

	const applyPresetRange = (days: number | null, label: string) => {
		if (days === null) {
			startDate = '';
			endDate = '';
			selectedRange = label;
			return;
		}
		const end = new Date();
		const start = new Date();
		start.setDate(end.getDate() - days + 1);
		startDate = formatDateInput(start);
		endDate = formatDateInput(end);
		selectedRange = label;
	};

	applyPresetRange(null, 'All time');

	const buildFilterParams = () => {
		const params: Record<string, string | number> = {};
		if (statusFilter) params.status = statusFilter;
		if (searchQuery.trim()) params[searchField] = searchQuery.trim();
		const startUnix = toUnixStart(startDate);
		const endUnix = toUnixEnd(endDate);
		if (startUnix) params.start_date = startUnix;
		if (endUnix) params.end_date = endUnix;
		return params;
	};

	let filterParams: Record<string, string | number> = buildFilterParams();
	let filterKey = '';
	let lastFilterKey = '';
	let lastPageSize = transactionsPageSize;
	let planFilterKey = '';
	let lastPlanFilterKey = '';

	const getTransactions = async (filters: Record<string, string | number>) => {
		transactionsLoading = true;
		try {
			const res = await adminListPaymentTransactions(localStorage.token, {
				...filters,
				page: transactionsPage,
				page_size: transactionsPageSize
			});
			transactions = res?.data ?? [];
			transactionsTotal = res?.total ?? 0;
		} catch (error) {
			toast.error(`${error}`);
			transactions = [];
			transactionsTotal = 0;
		} finally {
			transactionsLoading = false;
		}
	};

	const getUserTotalFromTransactions = async (
		userId: string,
		filters: Record<string, string | number>
	) => {
		let page = 1;
		const pageSize = 100;
		let total = 0;
		let currency: string | null = null;
		let totalRecords = 0;
		let loaded = 0;

		do {
			const res = await adminListPaymentTransactions(localStorage.token, {
				...filters,
				user_id: userId,
				page,
				page_size: pageSize
			});
			const items = res?.data ?? [];
			totalRecords = res?.total ?? 0;
			items.forEach((item: PaymentTransaction) => {
				const amountValue = Number(item.amount ?? 0);
				if (!Number.isNaN(amountValue)) {
					total += amountValue;
				}
				if (!currency && item.currency) {
					currency = item.currency;
				}
			});
			loaded += items.length;
			page += 1;
		} while (loaded < totalRecords && totalRecords > 0);

		return { total_amount: total, currency };
	};

	const getCustomers = async () => {
		customersLoading = true;
		try {
			const res = await getUsers(localStorage.token, '', 'created_at', 'desc', 1);
			customers = res?.users ?? [];
			const filters = {
				status: statusFilter || undefined,
				start_date: toUnixStart(startDate),
				end_date: toUnixEnd(endDate)
			};
			const totalsEntries = await Promise.all(
				(customers ?? []).map(async (customer) => {
					const summary = await getUserTotalFromTransactions(customer.id, filters);
					return [customer.id, summary] as const;
				})
			);
			customersTotals = totalsEntries.reduce(
				(acc, [userId, summary]) => {
					acc[userId] = {
						total_amount: Number(summary.total_amount ?? 0),
						currency: summary.currency ?? null
					};
					return acc;
				},
				{} as Record<string, { total_amount: number; currency: string | null }>
			);
		} catch (error) {
			toast.error(`${error}`);
			customers = [];
			customersTotals = {};
		} finally {
			customersLoading = false;
		}
	};

	onMount(() => {
		getCustomers();
		getTotalMetrics();
		getRangeKpis();

		const refreshInterval = setInterval(() => {
			getTotalMetrics();
			getRangeKpis();
		}, 60000);

		return () => {
			clearInterval(refreshInterval);
		};
	});

	const getMetrics = async (filters: Record<string, string | number>) => {
		metricsLoading = true;
		try {
			const res = await adminPaymentMetrics(localStorage.token, filters);
			metrics = {
				total_amount: Number(res?.total_amount ?? 0),
				total_transactions: Number(res?.total_transactions ?? 0),
				avg_amount: Number(res?.avg_amount ?? 0),
				currency: res?.currency ?? null,
				status_breakdown: res?.status_breakdown ?? [],
				revenue_trend: res?.revenue_trend ?? []
			};
			markProviderSynced();
		} catch (error) {
			toast.error(`${error}`);
			metrics = {
				total_amount: 0,
				total_transactions: 0,
				avg_amount: 0,
				currency: null,
				status_breakdown: [],
				revenue_trend: []
			};
		} finally {
			metricsLoading = false;
		}
	};

	const getTotalMetrics = async () => {
		totalMetricsLoading = true;
		try {
			const payload = await adminPaymentKpis(localStorage.token);
			kpis = {
				mrr: Number(payload?.mrr ?? 0),
				arr: Number(payload?.arr ?? 0),
				active_subscriptions: Number(payload?.active_subscriptions ?? 0),
				arpu: Number(payload?.arpu ?? 0),
				churn: payload?.churn ?? null,
				currency: payload?.currency ?? null
			};
			markProviderSynced();
		} catch (error) {
			toast.error(`${error}`);
			kpis = {
				mrr: 0,
				arr: 0,
				active_subscriptions: 0,
				arpu: 0,
				churn: null,
				currency: null
			};
		} finally {
			totalMetricsLoading = false;
		}
	};

	const getRangeKpis = async () => {
		rangeKpisLoading = true;
		try {
			const payload = await adminPaymentKpis(localStorage.token, {
				start_date: toUnixStart(startDate),
				end_date: toUnixEnd(endDate)
			});
			rangeKpis = {
				mrr: Number(payload?.mrr ?? 0),
				arr: Number(payload?.arr ?? 0),
				active_subscriptions: Number(payload?.active_subscriptions ?? 0),
				arpu: Number(payload?.arpu ?? 0),
				churn: payload?.churn ?? null,
				currency: payload?.currency ?? null
			};
			markProviderSynced();
		} catch (error) {
			toast.error(`${error}`);
			rangeKpis = {
				mrr: 0,
				arr: 0,
				active_subscriptions: 0,
				arpu: 0,
				churn: null,
				currency: null
			};
		} finally {
			rangeKpisLoading = false;
		}
	};

	const getPlanSummaries = async (filters: { start_date?: number; end_date?: number }) => {
		plansLoading = true;
		try {
			const res = await adminPaymentPlansSummary(localStorage.token, {
				start_date: filters.start_date,
				end_date: filters.end_date
			});
			planSummaries = (res?.data ?? []).map(
				(item: { plan_id?: string; total_amount?: number; total_transactions?: number; currency?: string | null }) => ({
					plan_id: String(item.plan_id ?? '').trim().toLowerCase(),
					total_amount: Number(item.total_amount ?? 0),
					total_transactions: Number(item.total_transactions ?? 0),
					currency: item.currency ?? null
				})
			);
			const totalsEntries = await Promise.all(
				pricingPlans.map(async (plan) => {
					const planId = String(plan.planId ?? '').trim();
					if (!planId) return null;
					const total = await adminPlanTotalAmount(localStorage.token, planId);
					return [
						planId.toLowerCase(),
						{
							total_amount: Number(total?.total_amount ?? 0),
							total_transactions: Number(total?.total_transactions ?? 0),
							currency: total?.currency ?? null
						}
					] as const;
				})
			);
			planTotals = totalsEntries.reduce(
				(acc, entry) => {
					if (!entry) return acc;
					const [planId, total] = entry;
					acc[planId] = total;
					return acc;
				},
				{} as Record<
					string,
					{ total_amount: number; total_transactions: number; currency?: string | null }
				>
			);
		} catch (error) {
			toast.error(`${error}`);
			planSummaries = [];
			planTotals = {};
		} finally {
			plansLoading = false;
		}
	};

	$: filterParams = buildFilterParams();
	$: filterKey = JSON.stringify(filterParams);
	$: if (filterKey !== lastFilterKey) {
		lastFilterKey = filterKey;
		transactionsPage = 1;
	}
	$: if (transactionsPage) {
		getTransactions(filterParams);
	}
	$: if (filterParams) {
		getMetrics(filterParams);
	}
	$: {
		planFilterKey = JSON.stringify({
			start_date: toUnixStart(startDate),
			end_date: toUnixEnd(endDate)
		});
		if (planFilterKey !== lastPlanFilterKey) {
			lastPlanFilterKey = planFilterKey;
			getPlanSummaries({
				start_date: toUnixStart(startDate),
				end_date: toUnixEnd(endDate)
			});
		}
	}
	$: if (transactionsPageSize !== lastPageSize) {
		lastPageSize = transactionsPageSize;
		transactionsPage = 1;
		getTransactions(filterParams);
	}
	$: {
		const items = [...(transactions ?? [])];
		items.sort((a, b) => {
			const dir = sortDirection === 'asc' ? 1 : -1;
			if (sortKey === 'amount') {
				const aVal = Number(a.amount ?? 0);
				const bVal = Number(b.amount ?? 0);
				return (aVal - bVal) * dir;
			}
			if (sortKey === 'status') {
				const aVal = String(a.status ?? '').toLowerCase();
				const bVal = String(b.status ?? '').toLowerCase();
				return aVal.localeCompare(bVal) * dir;
			}
			return ((a.created_at ?? 0) - (b.created_at ?? 0)) * dir;
		});
		sortedTransactions = items;
	}

	const handleExport = async () => {
		exportLoading = true;
		try {
			const blob = await adminExportPaymentTransactions(localStorage.token, buildFilterParams());
			if (!blob || blob.size === 0) {
				toast.error('No transactions to export.');
				return;
			}
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `payment-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
			link.style.display = 'none';
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			exportLoading = false;
		}
	};

	const formatShortDate = (timestamp: number) => {
		const date = new Date(timestamp * 1000);
		if (Number.isNaN(date.getTime())) return '';
		return new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit' }).format(date);
	};

	const buildTrendSeries = (items: { date: string; amount: number; count: number }[]) =>
		items
			.map((item) => ({
				label: item.date,
				value: item.amount,
				timestamp: Math.floor(new Date(item.date).getTime() / 1000)
			}))
			.sort((a, b) => a.timestamp - b.timestamp);

	const chartWidth = 240;
	const chartHeight = 84;
	const chartPadding = 6;
	const barGap = 6;

	let trendSeries: { label: string; value: number; timestamp: number }[] = [];
	let trendPolyline = '';
	let trendArea = '';
	let trendTotal = 0;
	let trendCurrency = '';
	let revenueBars: { x: number; y: number; width: number; height: number; value: number }[] = [];
	let statusSeries: { status: string; count: number }[] = [];
	type PieSlice = { status: string; count: number; percent: number; d: string; color: string };
	let statusTotal = 0;
	let pieSlices: PieSlice[] = [];
	let fallbackTotalAmount = 0;
	let fallbackCurrency = '';
	let sortedTransactions: PaymentTransaction[] = [];
	let isUserSearchActive = false;
	let userSearchDetails:
		| {
				query: string;
				total: number;
				amount: number;
				currency: string;
		  }
		| null = null;

	const buildSparkline = (values: number[]) => {
		if (values.length === 0) return { points: [] as string[] };
		const max = Math.max(...values);
		const min = Math.min(...values);
		const range = max - min || 1;
		return values.reduce(
			(acc, value, index) => {
				const x =
					chartPadding +
					(index / Math.max(values.length - 1, 1)) * (chartWidth - chartPadding * 2);
				const y =
					chartPadding +
					(1 - (value - min) / range) * (chartHeight - chartPadding * 2);
				acc.points.push(`${x.toFixed(2)},${y.toFixed(2)}`);
				return acc;
			},
			{ points: [] as string[] }
		);
	};

	$: fallbackTotalAmount = (transactions ?? []).reduce((sum, item) => {
		const amountValue = Number(item.amount ?? 0);
		return Number.isNaN(amountValue) ? sum : sum + amountValue;
	}, 0);
	$: fallbackCurrency = transactions?.find((item) => item.currency)?.currency ?? '';

	$: trendSeries =
		metrics.revenue_trend && metrics.revenue_trend.length > 0
			? buildTrendSeries(metrics.revenue_trend)
			: buildTrendSeries(
					(transactions ?? []).map((item) => ({
						date: new Date(item.created_at * 1000).toISOString().slice(0, 10),
						amount: Number(item.amount ?? 0),
						count: 1
					}))
			  );
	$: trendTotal = trendSeries.reduce((sum, item) => sum + item.value, 0);
	$: trendCurrency = metrics.currency ?? fallbackCurrency ?? '';
	$: {
		if (metrics.status_breakdown && metrics.status_breakdown.length > 0) {
			statusSeries = metrics.status_breakdown
				.map((item) => ({ status: item.status ?? 'unknown', count: item.count }))
				.sort((a, b) => b.count - a.count);
		} else {
			const counts: Record<string, number> = {};
			(transactions ?? []).forEach((item) => {
				const statusKey = (item.status ?? 'unknown').toLowerCase();
				counts[statusKey] = (counts[statusKey] ?? 0) + 1;
			});
			statusSeries = Object.entries(counts)
				.map(([status, count]) => ({ status, count }))
				.sort((a, b) => b.count - a.count);
		}
	}

	const pieSize = 120;
	const pieCenter = pieSize / 2;
	const pieOuterRadius = 44;
	const pieInnerRadius = 26;

	const getStatusColor = (status: string) => {
		const key = (status ?? 'unknown').toLowerCase();
		if (['active', 'trialing', 'executed', 'confirmed', 'completed', 'success'].includes(key)) return '#10b981'; // emerald-500
		if (['failed', 'canceled'].includes(key)) return '#f43f5e'; // rose-500
		if (['past_due', 'pending'].includes(key)) return '#f59e0b'; // amber-500
		if (['created'].includes(key)) return '#3b82f6'; // blue-500
		return '#94a3b8'; // slate-400
	};

	const polarToCartesian = (cx: number, cy: number, radius: number, angleDeg: number) => {
		const angleRad = ((angleDeg - 90) * Math.PI) / 180;
		return { x: cx + radius * Math.cos(angleRad), y: cy + radius * Math.sin(angleRad) };
	};

	const describeDonutSegment = (
		cx: number,
		cy: number,
		outerRadius: number,
		innerRadius: number,
		startAngle: number,
		endAngle: number
	) => {
		const startOuter = polarToCartesian(cx, cy, outerRadius, startAngle);
		const endOuter = polarToCartesian(cx, cy, outerRadius, endAngle);
		const startInner = polarToCartesian(cx, cy, innerRadius, endAngle);
		const endInner = polarToCartesian(cx, cy, innerRadius, startAngle);
		const sweep = Math.max(endAngle - startAngle, 0);
		const largeArcFlag = sweep > 180 ? 1 : 0;
		return [
			`M ${startOuter.x} ${startOuter.y}`,
			`A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
			`L ${startInner.x} ${startInner.y}`,
			`A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${endInner.x} ${endInner.y}`,
			'Z'
		].join(' ');
	};

	$: statusTotal = statusSeries.reduce((sum, item) => sum + (Number(item.count) || 0), 0);
	$: pieSlices = (() => {
		if (!statusTotal) return [];
		let cursor = 0;
		return statusSeries
			.filter((item) => (Number(item.count) || 0) > 0)
			.map((item) => {
				const count = Number(item.count) || 0;
				const percent = count / statusTotal;
				const startAngle = cursor * 360;
				cursor += percent;
				const endAngle = cursor * 360;
				const d = describeDonutSegment(
					pieCenter,
					pieCenter,
					pieOuterRadius,
					pieInnerRadius,
					startAngle,
					endAngle
				);
				return {
					status: item.status,
					count,
					percent,
					d,
					color: getStatusColor(item.status)
				};
			});
	})();
	$: {
		const values = trendSeries.map((item) => item.value);
		const { points } = buildSparkline(values);
		if (points.length) {
			trendPolyline = points.join(' ');
			trendArea = `${points.join(' ')} ${chartWidth - chartPadding},${chartHeight - chartPadding} ${chartPadding},${chartHeight - chartPadding}`;
		} else {
			trendPolyline = '';
			trendArea = '';
		}
	}
	$: {
		const values = trendSeries.map((item) => item.value);
		if (values.length === 0) {
			revenueBars = [];
		} else {
			const max = Math.max(...values);
			const range = max || 1;
			const barCount = values.length;
			const availableWidth = chartWidth - chartPadding * 2;
			const totalGap = barGap * Math.max(barCount - 1, 0);
			const barWidth = Math.max((availableWidth - totalGap) / Math.max(barCount, 1), 2);
			revenueBars = values.map((value, index) => {
				const height = ((value / range) * (chartHeight - chartPadding * 2)) || 1;
				const x = chartPadding + index * (barWidth + barGap);
				const y = chartHeight - chartPadding - height;
				return { x, y, width: barWidth, height, value };
			});
		}
	}

	const resetFilters = () => {
		statusFilter = '';
		searchField = 'payment_id';
		searchQuery = '';
		applyPresetRange(null, 'All time');
		getRangeKpis();
	};

	const applyFilters = () => {
		transactionsPage = 1;
		const params = buildFilterParams();
		getTransactions(params);
		getMetrics(params);
		getRangeKpis();
		getCustomers();
		getPlanSummaries({
			start_date: toUnixStart(startDate),
			end_date: toUnixEnd(endDate)
		});
	};

	const getChartMetric = (chart: { title: string; metric: string }) => {
		if (chart.title === 'Revenue trend') {
			if (metricsLoading) return chart.metric;
			return formatAmount(trendTotal || fallbackTotalAmount, trendCurrency || 'BDT');
		}
		if (chart.title === 'Status breakdown') {
			return metrics.total_transactions
				? `${metrics.total_transactions}`
				: transactionsTotal
					? `${transactionsTotal}`
					: chart.metric;
		}
		return chart.metric;
	};

	const getKpis = () => {
		const currency = (kpis.currency ?? fallbackCurrency) || undefined;
		const totalAmount = kpis.mrr || fallbackTotalAmount;
		const avgAmount = kpis.arpu || (transactionsTotal ? fallbackTotalAmount / transactionsTotal : 0);
		return [
			{
				title: 'MRR',
				value: formatAmount(totalAmount, currency),
				change: '',
				trend: 'up',
				tone: 'positive',
				note: 'filtered revenue'
			},
			{
				title: 'ARR',
				value: formatAmount(kpis.arr || totalAmount * 12, currency),
				change: '',
				trend: 'up',
				tone: 'positive',
				note: 'annualized run rate'
			},
			{
				title: 'Active subscriptions',
				value: `${kpis.active_subscriptions ?? 0}`,
				change: '',
				trend: 'up',
				tone: 'positive',
				note: 'transactions in range'
			},
			{
				title: 'Churn',
				value: kpis.churn === null || kpis.churn === undefined ? '—' : `${kpis.churn}%`,
				change: '',
				trend: 'down',
				tone: 'positive',
				note: 'requires subscription data'
			},
			{
				title: 'ARPU',
				value: formatAmount(avgAmount, currency),
				change: '',
				trend: 'up',
				tone: 'positive',
				note: 'avg per transaction'
			}
		];
	};

	const isEmailSearch = (value: string) => value.includes('@');

	$: isUserSearchActive = searchField === 'user_query' && searchQuery.trim().length > 0;
	$: userSearchDetails = isUserSearchActive
		? {
				query: searchQuery.trim(),
				total: transactionsTotal,
				amount: sortedTransactions.reduce((sum, item) => sum + Number(item.amount ?? 0), 0),
				currency: metrics.currency ?? fallbackCurrency ?? 'BDT'
			}
		: null;

	$: {
		const summaryMap = planSummaries.reduce(
			(acc, item) => {
				acc[item.plan_id] = item;
				return acc;
			},
			{} as Record<string, (typeof planSummaries)[number]>
		);
		const totalsMap = planTotals;
		const totalCompleted = planSummaries.reduce(
			(sum, item) => sum + Number(item.total_transactions ?? 0),
			0
		);
		planRows = pricingPlans.map((plan) => {
			const planKey = String(plan.planId ?? '').trim().toLowerCase();
			const summary = summaryMap[planKey];
			const totals = totalsMap[planKey];
			const transactions = Number(totals?.total_transactions ?? summary?.total_transactions ?? 0);
			const revenue = Number(totals?.total_amount ?? summary?.total_amount ?? 0);
			const conversion =
				totalCompleted > 0 ? `${((transactions / totalCompleted) * 100).toFixed(1)}%` : '0%';
			return {
				name: plan.name,
				price: plan.price,
				period: plan.period,
				subs: `${transactions}`,
				revenue: formatAmount(revenue, totals?.currency ?? summary?.currency ?? plan.currency),
				conversion
			};
		});
	}

	const getStatusBarStyle = (status: string, count: number, max: number) => {
		const width = max ? Math.max((count / max) * 100, 6) : 0;
		return `width: ${width}%;`;
	};

	const setSort = (key: 'created_at' | 'amount' | 'status') => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = 'desc';
		}
	};
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
								selectedRange === range.label
									? 'bg-[rgba(146,39,143,1)] text-white shadow-sm'
									: 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'
							}`}
							type="button"
							on:click={() => applyPresetRange(range.days, range.label)}
						>
							{$i18n.t(range.label)}
						</button>
					{/each}
				</div>
				<button
					class="inline-flex items-center rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
					type="button"
					on:click={handleExport}
					disabled={exportLoading}
				>
					{$i18n.t(exportLoading ? 'Exporting' : 'Export')}
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
		<div class="mb-4 h-1 w-12 rounded-full bg-gradient-to-r from-[rgba(146,39,143,1)] to-transparent"></div>
		<div class="flex flex-col gap-4">
			<div class="flex flex-wrap items-end gap-4 text-sm">
				<div class="flex flex-col gap-1">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Status')}
					</label>
					<select
						class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
						bind:value={statusFilter}
					>
						{#each statusOptions as option}
							<option value={option.value}>{$i18n.t(option.label)}</option>
						{/each}
					</select>
				</div>

				<div class="flex flex-col gap-1">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Search by')}
					</label>
					<select
						class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
						bind:value={searchField}
					>
						<option value="payment_id">{$i18n.t('Payment ID')}</option>
						<option value="trx_id">{$i18n.t('Transaction ID')}</option>
						<option value="merchant_invoice_number">{$i18n.t('Invoice number')}</option>
						<option value="user_query">{$i18n.t('Email / Name / Username')}</option>
						<option value="user_id">{$i18n.t('User ID')}</option>
					</select>
				</div>

				<div class="flex flex-1 flex-col gap-1 min-w-[220px]">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Search')}
					</label>
					<input
						class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
						type="text"
						bind:value={searchQuery}
						placeholder={$i18n.t('Enter value')}
					/>
				</div>

				<div class="flex flex-col gap-1">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Start date')}
					</label>
					<input
						class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
						type="date"
						bind:value={startDate}
						on:change={() => (selectedRange = 'Custom')}
					/>
				</div>

				<div class="flex flex-col gap-1">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('End date')}
					</label>
					<input
						class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
						type="date"
						bind:value={endDate}
						on:change={() => (selectedRange = 'Custom')}
					/>
				</div>

				<div class="flex flex-col gap-1">
					<label class="text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Actions')}
					</label>
					<div class="flex flex-wrap gap-2">
						<select
							class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
							bind:value={transactionsPageSize}
							title="Rows per page"
						>
							<option value={8}>8 / page</option>
							<option value={15}>15 / page</option>
							<option value={30}>30 / page</option>
							<option value={50}>50 / page</option>
						</select>
						<button
							class="inline-flex items-center rounded-lg bg-[rgba(146,39,143,1)] px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:opacity-90"
							type="button"
							on:click={applyFilters}
						>
							{$i18n.t('Search')}
						</button>
						<button
							class="inline-flex items-center rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
							type="button"
							on:click={resetFilters}
						>
							{$i18n.t('Reset')}
						</button>
					</div>
				</div>
			</div>
			<div class="text-xs text-gray-400">
				{$i18n.t('Filters apply to the transactions list and charts.')}
			</div>
		</div>
	</section>
	<section
		class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
	>
		<div class="mb-4 flex items-start justify-between gap-3">
			<div>
				<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('KPIs')}
				</h2>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('MRR, ARR, ARPU for completed payments')}
				</p>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-400">
					{rangeKpisLoading ? $i18n.t('Loading') : $i18n.t('Live')}
				</span>
				<button
					class="inline-flex items-center rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
					type="button"
					on:click={getRangeKpis}
					disabled={rangeKpisLoading}
				>
					{$i18n.t('Refresh')}
				</button>
			</div>
		</div>

		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('MRR')}</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{formatAmount(rangeKpis.mrr, rangeKpis.currency ?? fallbackCurrency ?? undefined)}
				</div>
			</article>
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('ARR')}</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{formatAmount(rangeKpis.arr, rangeKpis.currency ?? fallbackCurrency ?? undefined)}
				</div>
			</article>
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
					{$i18n.t('Active subscriptions')}
				</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{rangeKpis.active_subscriptions}
				</div>
			</article>
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('ARPU')}</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{formatAmount(rangeKpis.arpu, rangeKpis.currency ?? fallbackCurrency ?? undefined)}
				</div>
			</article>
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Churn')}</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{rangeKpis.churn === null || rangeKpis.churn === undefined ? '—' : `${rangeKpis.churn}%`}
				</div>
			</article>
			<article class="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Currency')}</div>
				<div class="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
					{rangeKpis.currency ?? fallbackCurrency ?? '—'}
				</div>
			</article>
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
					<span class="text-xs text-gray-400">{metricsLoading ? $i18n.t('Loading') : $i18n.t('Live')}</span>
				</div>
				<div class="mt-4 flex items-center justify-between gap-3">
					<div class="text-2xl font-semibold text-gray-900 dark:text-white">
						{getChartMetric(chart)}
					</div>
					{#if chart.change}
						<span
							class={`rounded-full px-2 py-0.5 text-xs font-semibold ${
								chart.tone === 'positive'
									? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200'
									: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200'
							}`}
						>
							{$i18n.t(chart.trend === 'up' ? 'Up' : 'Down')} {chart.change}
						</span>
					{/if}
				</div>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t(chart.footnote)}</p>
				{#if chart.title === 'Revenue trend'}
					<div class="mt-4 rounded-xl border border-dashed border-gray-200 bg-gradient-to-br from-gray-50 via-white to-[rgba(146,39,143,0.04)] p-4 dark:border-gray-700 dark:from-gray-950 dark:via-gray-900 dark:to-[rgba(146,39,143,0.08)]">
						{#if trendSeries.length === 0}
							<div class="flex h-24 items-center justify-center text-xs text-gray-400">
								{$i18n.t('No transaction data for this range.')}
							</div>
						{:else}
							<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
								<span>{$i18n.t('From')} {formatShortDate(trendSeries[0].timestamp)}</span>
								<span>{$i18n.t('To')} {formatShortDate(trendSeries[trendSeries.length - 1].timestamp)}</span>
							</div>
							<svg
								class="mt-3 h-[84px] w-full"
								viewBox={`0 0 ${chartWidth} ${chartHeight}`}
								preserveAspectRatio="none"
								aria-hidden="true"
							>
								<defs>
									<linearGradient id="trendGradient" x1="0" x2="0" y1="0" y2="1">
										<stop offset="0%" stop-color="rgba(146,39,143,0.55)" />
										<stop offset="100%" stop-color="rgba(146,39,143,0.12)" />
									</linearGradient>
									<linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
										<stop offset="0%" stop-color="rgba(146,39,143,0.4)" />
										<stop offset="100%" stop-color="rgba(146,39,143,0)" />
									</linearGradient>
								</defs>
								{#each revenueBars as bar, index (index)}
									<rect
										x={bar.x}
										y={bar.y}
										width={bar.width}
										height={bar.height}
										rx="3"
										fill="url(#trendGradient)"
									>
										<title>
											{trendSeries[index]?.label}: {formatAmount(bar.value, trendCurrency || 'BDT')}
										</title>
									</rect>
								{/each}
								<polyline
									fill="none"
									stroke="rgba(146,39,143,0.6)"
									stroke-width="1.5"
									points={trendPolyline}
									vector-effect="non-scaling-stroke"
								/>
								<polygon fill="url(#trendFill)" points={trendArea} />
							</svg>
						{/if}
					</div>
				{:else if chart.title === 'Status breakdown'}
					<div class="mt-4 rounded-xl border border-dashed border-gray-200 bg-gradient-to-br from-gray-50 via-white to-[rgba(146,39,143,0.04)] p-4 dark:border-gray-700 dark:from-gray-950 dark:via-gray-900 dark:to-[rgba(146,39,143,0.08)]">
						{#if statusSeries.length === 0}
							<div class="flex h-24 items-center justify-center text-xs text-gray-400">
								{$i18n.t('No transactions for this filter.')}
							</div>
						{:else}
							<div class="grid gap-4 sm:grid-cols-[140px_1fr] sm:items-center">
								<div class="flex items-center justify-center">
									<svg
										class="h-[120px] w-[120px]"
										viewBox={`0 0 ${pieSize} ${pieSize}`}
										role="img"
										aria-label={$i18n.t('Transactions by status')}
									>
										<circle
											cx={pieCenter}
											cy={pieCenter}
											r={pieOuterRadius}
											fill="transparent"
											stroke="rgba(148,163,184,0.25)"
											stroke-width={pieOuterRadius - pieInnerRadius}
										/>
										{#each pieSlices as slice (slice.status)}
											<path d={slice.d} fill={slice.color}>
												<title>
													{getStatusLabel(slice.status)}: {slice.count} (
													{Math.round(slice.percent * 100)}%)
												</title>
											</path>
										{/each}
										<text
											x={pieCenter}
											y={pieCenter - 2}
											text-anchor="middle"
											class="fill-gray-900 text-[12px] font-semibold dark:fill-gray-100"
										>
											{statusTotal}
										</text>
										<text
											x={pieCenter}
											y={pieCenter + 14}
											text-anchor="middle"
											class="fill-gray-500 text-[9px] font-medium dark:fill-gray-400"
										>
											{$i18n.t('Total')}
										</text>
									</svg>
								</div>

								<div>
									{#each statusSeries as item (item.status)}
										<div class="mb-3 last:mb-0">
											<div class="flex items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
												<span class="inline-flex items-center gap-2">
													<span
														class="h-2.5 w-2.5 rounded-full"
														style={`background-color: ${getStatusColor(item.status)}`}
													></span>
													{$i18n.t(getStatusLabel(item.status))}
												</span>
												<span class="tabular-nums">
													{item.count}
													{#if statusTotal}
														<span class="text-gray-400 dark:text-gray-500">
															({Math.round((item.count / statusTotal) * 100)}%)
														</span>
													{/if}
												</span>
											</div>
											<div class="mt-1 h-2 rounded-full bg-gray-200 dark:bg-gray-800">
												<div
													class={`h-2 rounded-full ${getStatusClass(item.status)}`}
													style={getStatusBarStyle(item.status, item.count, statusSeries[0].count)}
												></div>
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<div
						class="mt-4 h-40 rounded-xl border border-dashed border-gray-200 bg-gradient-to-br from-gray-50 via-white to-[rgba(146,39,143,0.04)] dark:border-gray-700 dark:from-gray-950 dark:via-gray-900 dark:to-[rgba(146,39,143,0.08)]"
					></div>
				{/if}
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
					{$i18n.t('Recent transactions')}
				</h2>
				<button
					class="text-xs font-semibold text-[rgba(146,39,143,1)] transition hover:opacity-80"
					type="button"
				>
					{$i18n.t('View all')}
				</button>
			</div>
			<div class="mt-4 text-sm">
				{#if transactionsLoading}
					<div class="py-6">
						<Spinner className="size-5" />
					</div>
				{:else if !transactions || transactions.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 p-4 text-center text-xs text-gray-500 dark:border-gray-800 dark:text-gray-400">
						{$i18n.t('No transactions found.')}
					</div>
				{:else}
					{#if isUserSearchActive && userSearchDetails && isEmailSearch(userSearchDetails.query)}
						<div class="mb-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-xs text-gray-600 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
							<div class="flex flex-wrap items-center justify-between gap-2">
								<div>
									<div class="text-[11px] uppercase tracking-wide text-gray-400">
										{$i18n.t('User payment details')}
									</div>
									<div class="text-sm font-semibold text-gray-900 dark:text-white">
										{userSearchDetails.query}
									</div>
								</div>
								<div class="flex flex-wrap items-center gap-4">
									<div class="text-xs">
										<span class="text-gray-400">{$i18n.t('Transactions')}</span>
										<span class="ml-2 font-semibold text-gray-900 dark:text-white">
											{userSearchDetails.total}
										</span>
									</div>
									<div class="text-xs">
										<span class="text-gray-400">{$i18n.t('Total')}</span>
										<span class="ml-2 font-semibold text-gray-900 dark:text-white">
											{formatAmount(userSearchDetails.amount, userSearchDetails.currency)}
										</span>
									</div>
								</div>
							</div>
							<div class="mt-3 overflow-x-auto">
								<table class="min-w-[520px] w-full text-xs">
									<thead class="uppercase tracking-wide text-gray-400">
										<tr>
											<th class="pb-2 text-left font-medium">{$i18n.t('Invoice')}</th>
											<th class="pb-2 text-left font-medium">{$i18n.t('Date')}</th>
											<th class="pb-2 text-left font-medium">{$i18n.t('Amount')}</th>
											<th class="pb-2 text-left font-medium">{$i18n.t('Status')}</th>
										</tr>
									</thead>
									<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
										{#each sortedTransactions as transaction}
											<tr>
												<td class="py-2 text-gray-900 dark:text-white">
													{transaction.merchant_invoice_number || transaction.payment_id || transaction.id}
												</td>
												<td class="py-2 text-gray-500 dark:text-gray-400">
													{formatDate(transaction.created_at)}
												</td>
												<td class="py-2 text-gray-900 dark:text-white">
													{formatAmount(transaction.amount ?? undefined, transaction.currency ?? undefined)}
												</td>
												<td class="py-2">
													<span class={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${getStatusClass(transaction.status ?? 'unknown')}`}>
														{$i18n.t(getStatusLabel(transaction.status ?? 'unknown'))}
													</span>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</div>
					{/if}
					<div class="overflow-x-auto">
						<table class="min-w-[720px] w-full text-sm">
							<thead class="text-xs uppercase tracking-wide text-gray-400">
								<tr>
									<th class="pb-3 text-left font-medium">{$i18n.t('Payment')}</th>
									<th class="pb-3 text-left font-medium">{$i18n.t('User')}</th>
									<th class="pb-3 text-left font-medium">
										<button type="button" class="inline-flex items-center gap-1" on:click={() => setSort('amount')} title="Sort by amount">
											{$i18n.t('Amount')}
											<span class="text-[10px]">{sortKey === 'amount' ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
										</button>
									</th>
									<th class="pb-3 text-left font-medium">
										<button type="button" class="inline-flex items-center gap-1" on:click={() => setSort('status')} title="Sort by status">
											{$i18n.t('Status')}
											<span class="text-[10px]">{sortKey === 'status' ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
										</button>
									</th>
									<th class="pb-3 text-left font-medium">
										<button type="button" class="inline-flex items-center gap-1" on:click={() => setSort('created_at')} title="Sort by date">
											{$i18n.t('Created')}
											<span class="text-[10px]">{sortKey === 'created_at' ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
										</button>
									</th>
									<th class="pb-3 text-left font-medium">{$i18n.t('Trx')}</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
								{#each sortedTransactions as transaction}
									<tr>
										<td class="py-3 text-gray-900 dark:text-white">
											<div class="font-semibold">{transaction.merchant_invoice_number || transaction.payment_id || transaction.id}</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">{transaction.payment_id ?? '-'}</div>
										</td>
										<td class="py-3 text-gray-500 dark:text-gray-400">{getUserLabel(transaction)}</td>
										<td class="py-3 text-gray-900 dark:text-white">
											{formatAmount(transaction.amount ?? undefined, transaction.currency ?? undefined)}
										</td>
										<td class="py-3">
											<span class={`rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusClass(transaction.status ?? 'unknown')}`}>
												{$i18n.t(getStatusLabel(transaction.status ?? 'unknown'))}
											</span>
										</td>
										<td class="py-3 text-gray-500 dark:text-gray-400">{formatDate(transaction.created_at)}</td>
										<td class="py-3 text-gray-500 dark:text-gray-400">{transaction.trx_id ?? '-'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>

					{#if transactionsTotal > transactionsPageSize}
						<div class="mt-3 flex justify-end">
							<Pagination
								bind:page={transactionsPage}
								count={transactionsTotal}
								perPage={transactionsPageSize}
							/>
						</div>
					{/if}
				{/if}
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
			<table class="min-w-[760px] w-full text-sm">
				<thead class="text-xs uppercase tracking-wide text-gray-400">
					<tr>
						<th class="pb-3 text-left font-medium">{$i18n.t('Customer')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Role')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Total amount')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Created')}</th>
						<th class="pb-3 text-left font-medium">{$i18n.t('Last active')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
					{#if customersLoading}
						<tr>
							<td class="py-6 text-center text-xs text-gray-500 dark:text-gray-400" colspan="5">
								{$i18n.t('Loading customers...')}
							</td>
						</tr>
					{:else if customers.length === 0}
						<tr>
							<td class="py-6 text-center text-xs text-gray-500 dark:text-gray-400" colspan="5">
								{$i18n.t('No customers found.')}
							</td>
						</tr>
					{:else}
						{#each customers as customer}
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
								<td class="py-3 text-gray-900 dark:text-white">
									{formatAmount(
										customersTotals[customer.id]?.total_amount ?? 0,
										customersTotals[customer.id]?.currency ?? 'BDT'
									)}
								</td>
								<td class="py-3 text-gray-500 dark:text-gray-400">
									{formatDate(customer.created_at ?? null)}
								</td>
								<td class="py-3 text-gray-500 dark:text-gray-400">
									{formatLastActive(customer.last_active_at ?? null)}
								</td>
							</tr>
						{/each}
					{/if}
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
					<span class="text-xs text-gray-400">{$i18n.t('Live')}</span>
				</div>
				<dl class="mt-4 grid gap-3 text-sm">
					{#each section.items as item}
						<div class="flex items-center justify-between gap-4">
							<dt class="text-gray-500 dark:text-gray-400">{$i18n.t(item.label)}</dt>
							<dd class="font-semibold text-gray-900 dark:text-white">
								{#if section.title === 'Payment provider' && item.label === 'Last sync'}
									{providerLastSyncAt ? formatLastActive(providerLastSyncAt) : '—'}
								{:else}
									{$i18n.t(item.value)}
								{/if}
							</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/each}
	</section>
</div>
