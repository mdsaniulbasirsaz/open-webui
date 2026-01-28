<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		getTokenUsageSeries,
		getTokenUsageSummary,
		getTokenUsageActivityDetail,
		getTokenUsageByModel,
		getTokenUsageActivity
	} from '$lib/apis/token_usage';

	const i18n = getContext('i18n');

	let loadingSummary = true;
	let loadingSeries = true;
	let loadingModels = true;
	let loadingActivity = true;
	let errorSummary: string | null = null;
	let errorSeries: string | null = null;
	let errorModels: string | null = null;
	let errorActivity: string | null = null;

	let summaryCards = [
		{ label: 'Used (%)', value: '--' },
		{ label: 'Window start (UTC)', value: '--' },
		{ label: 'Used (tokens)', value: '--' },
		{ label: 'Limit (tokens)', value: '--' },
		{ label: 'Remaining (tokens)', value: '--' },
		{ label: 'Reserved (tokens)', value: '--' }
	];

	let usageSeries: { date: string; tokens: number; topModel?: string | null }[] = [];

	const buildRangeParams = () => {
		return {};
	};

	const handleError = (context: string, err: any) => {
		const message = err?.message ?? String(err);
		console.error(`[TokenUsage] ${context}`, err);
		toast.error(i18n.t('Failed to load token usage data'));
		return message;
	};

	const loadSummary = async () => {
		loadingSummary = true;
		errorSummary = null;
		try {
			const token = localStorage.token ?? '';
			const data = await getTokenUsageSummary(token, buildRangeParams());
			summaryCards = [
				{ label: 'Used (%)', value: `${Math.round(data.used_percent)}%` },
				{
					label: 'Window start (UTC)',
					value: new Date(data.window_start * 1000).toISOString().slice(0, 10)
				},
				{ label: 'Used (tokens)', value: data.used_tokens.toLocaleString() },
				{ label: 'Limit (tokens)', value: data.limit_tokens.toLocaleString() },
				{ label: 'Remaining (tokens)', value: data.remaining_tokens.toLocaleString() },
				{ label: 'Reserved (tokens)', value: data.reserved_tokens.toLocaleString() }
			];
		} catch (err: any) {
			errorSummary = handleError('summary', err);
		} finally {
			loadingSummary = false;
		}
	};

	const loadSeries = async () => {
		loadingSeries = true;
		errorSeries = null;
		try {
			const token = localStorage.token ?? '';
			const data = await getTokenUsageSeries(token, buildRangeParams());
			usageSeries = (data ?? []).map((item) => ({
				date: item.date,
				tokens: item.tokens,
				topModel: item.top_model ?? item.topModel ?? null
			}));
		} catch (err: any) {
			errorSeries = handleError('series', err);
		} finally {
			loadingSeries = false;
		}
	};

	const loadModelBreakdown = async () => {
		loadingModels = true;
		errorModels = null;
		try {
			const token = localStorage.token ?? '';
			modelBreakdown = await getTokenUsageByModel(token, buildRangeParams());
		} catch (err: any) {
			errorModels = handleError('models', err);
		} finally {
			loadingModels = false;
		}
	};

	const loadActivity = async () => {
		loadingActivity = true;
		errorActivity = null;
		try {
			const token = localStorage.token ?? '';
			const result = await getTokenUsageActivity(token, {
				...buildRangeParams(),
				page: activityPage,
				limit: activityPageSize
			});
			activityTotal = result?.total ?? 0;
			recentActivity = (result?.data ?? []).map((item) => ({
				id: item.id,
				time: new Date(item.timestamp * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
				model: item.model ?? null,
				type: item.type,
				input: item.input_tokens,
				output: item.output_tokens,
				total: item.total_tokens,
				conversationId: item.conversation_id ?? null
			}));
		} catch (err: any) {
			errorActivity = handleError('activity', err);
		} finally {
			loadingActivity = false;
		}
	};

	const totalPages = () => Math.max(1, Math.ceil(activityTotal / activityPageSize));

	const goToPage = (page: number) => {
		const next = Math.min(Math.max(1, page), totalPages());
		if (next !== activityPage) {
			activityPage = next;
			loadActivity();
		}
	};

	const refreshUsage = async () => {
		await Promise.all([loadSummary(), loadSeries(), loadModelBreakdown(), loadActivity()]);
	};

	onMount(() => {
		refreshUsage();
	});

	$: maxTokens = Math.max(...(usageSeries.length ? usageSeries.map((d) => d.tokens) : [1]));
	$: chartPoints = usageSeries
		.map((d, index) => {
			const x = usageSeries.length > 1 ? (index / (usageSeries.length - 1)) * 100 : 0;
			const y = 100 - (d.tokens / maxTokens) * 100;
			return `${x},${y}`;
		})
		.join(' ');

	let modelBreakdown: { model: string; tokens: number; share: number }[] = [];
	let recentActivity: {
		id: string;
		time: string;
		model: string | null;
		type: string;
		input: number;
		output: number;
		total: number;
		conversationId?: string | null;
	}[] = [];
	let activityPage = 1;
	let activityPageSize = 10;
	let activityTotal = 0;

	let showDrawer = false;
	let selectedActivityId: string | null = null;
	let activityDetail: any = null;
	let loadingDetail = false;
	let errorDetail: string | null = null;

	const openDetail = async (activityId: string) => {
		showDrawer = true;
		selectedActivityId = activityId;
		loadingDetail = true;
		errorDetail = null;
		activityDetail = null;
		try {
			const token = localStorage.token ?? '';
			activityDetail = await getTokenUsageActivityDetail(token, activityId);
		} catch (err: any) {
			errorDetail = handleError('activity-detail', err);
		} finally {
			loadingDetail = false;
		}
	};

	const closeDrawer = () => {
		showDrawer = false;
		selectedActivityId = null;
		activityDetail = null;
	};
</script>

<div id="tab-token-usage" class="pb-6 max-h-[42rem] overflow-y-auto pr-1">
	<div class="flex flex-col gap-1">
		<div class="text-base font-medium text-gray-900 dark:text-gray-100">
			{$i18n.t('Uses Token')}
		</div>
		<div class="text-sm text-blue-600 dark:text-blue-400">
			{$i18n.t('Track your token usage across models and time.')}
		</div>
	</div>

	<div
		class="mt-4 rounded-xl border border-blue-200/60 dark:border-blue-900/50 bg-blue-50/40 dark:bg-blue-950/30 p-4"
	>
		<div class="text-sm font-medium text-blue-800 dark:text-blue-200">
			{$i18n.t('Token Usage Overview')}
		</div>
	</div>

	<div class="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
		{#each summaryCards as card (card.label)}
			<div
				class="rounded-xl border border-green-200/60 dark:border-green-900/50 bg-green-50/40 dark:bg-green-950/30 px-4 py-3"
			>
				<div class="text-xs text-green-700 dark:text-green-300">
					{$i18n.t(card.label)}
				</div>
				<div class="mt-1 text-lg font-semibold text-green-800 dark:text-green-200">
					{loadingSummary ? '—' : card.value}
				</div>
			</div>
		{/each}
	</div>

	<div
		class="mt-4 rounded-xl border border-purple-200/60 dark:border-purple-900/50 bg-purple-50/30 dark:bg-purple-950/20 p-4"
		style="background-color: rgba(146, 39, 143, 0.04);"
	>
		<div class="flex items-center justify-between">
			<div class="text-sm font-medium" style="color: rgba(146, 39, 143, 1);">
				{$i18n.t('Token usage over time')}
			</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Live data')}
			</div>
		</div>
		<div class="mt-4 h-36 w-full">
			{#if loadingSeries}
				<div class="h-full w-full rounded-lg bg-gray-100/60 dark:bg-gray-800/60 animate-pulse"></div>
			{:else if errorSeries}
				<div class="text-sm text-red-600 dark:text-red-400">{errorSeries}</div>
			{:else}
				<svg viewBox="0 0 100 100" class="h-full w-full">
					<polyline
						points={chartPoints}
						fill="none"
						style="stroke: rgba(146, 39, 143, 1);"
						stroke-width="2"
						vector-effect="non-scaling-stroke"
					/>
					{#each usageSeries as point, index (point.date)}
						<circle
							cx={usageSeries.length > 1 ? (index / (usageSeries.length - 1)) * 100 : 0}
							cy={100 - (point.tokens / maxTokens) * 100}
							r="1.6"
							style="fill: rgba(146, 39, 143, 1);"
						/>
					{/each}
				</svg>
			{/if}
		</div>
		{#if !loadingSeries && !errorSeries}
			<div class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-gray-500 dark:text-gray-400">
				{#each usageSeries as point (point.date)}
					<div class="flex flex-col gap-0.5">
						<span>{point.date}</span>
						<span class="text-gray-800 dark:text-gray-200">
							{point.tokens.toLocaleString()} {$i18n.t('tokens')}
						</span>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<div class="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
		<div class="rounded-xl border border-blue-200/60 dark:border-blue-900/50 bg-blue-50/30 dark:bg-blue-950/20 p-4">
			<div class="text-sm font-medium text-blue-800 dark:text-blue-200">
				{$i18n.t('By Model')}
			</div>
			<div class="mt-3 overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-xs uppercase text-blue-600 dark:text-blue-300">
						<tr class="border-b border-gray-200 dark:border-gray-800">
							<th class="py-2 text-left font-medium">{$i18n.t('Model')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Tokens')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Share')}</th>
						</tr>
					</thead>
					<tbody>
						{#if loadingModels}
							<tr>
								<td class="py-3 text-sm text-blue-700 dark:text-blue-200" colspan="3">
									{$i18n.t('Loading...')}
								</td>
							</tr>
						{:else if errorModels}
							<tr>
								<td class="py-3 text-sm text-red-600 dark:text-red-400" colspan="3">
									{errorModels}
								</td>
							</tr>
						{:else if modelBreakdown.length === 0}
							<tr>
								<td class="py-3 text-sm text-blue-700 dark:text-blue-200" colspan="3">
									{$i18n.t('No usage data')}
								</td>
							</tr>
						{:else}
							{#each modelBreakdown as row (row.model)}
								<tr class="border-b border-gray-100 dark:border-gray-800 last:border-0">
									<td class="py-2 text-blue-900 dark:text-blue-100">{row.model}</td>
									<td class="py-2 text-right text-blue-700 dark:text-blue-200">
										{row.tokens.toLocaleString()}
									</td>
									<td class="py-2 text-right text-blue-700 dark:text-blue-200">{row.share}%</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		<div class="rounded-xl border border-green-200/60 dark:border-green-900/50 bg-green-50/30 dark:bg-green-950/20 p-4">
			<div class="text-sm font-medium text-green-800 dark:text-green-200">
				{$i18n.t('Recent Activity')}
			</div>
			<div class="mt-3 overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-xs uppercase text-green-600 dark:text-green-300">
						<tr class="border-b border-gray-200 dark:border-gray-800">
							<th class="py-2 text-left font-medium">{$i18n.t('Time')}</th>
							<th class="py-2 text-left font-medium">{$i18n.t('Model')}</th>
							<th class="py-2 text-left font-medium">{$i18n.t('Type')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Input')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Output')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Total')}</th>
							<th class="py-2 text-right font-medium">{$i18n.t('Details')}</th>
						</tr>
					</thead>
					<tbody>
						{#if loadingActivity}
							<tr>
								<td class="py-3 text-sm text-green-700 dark:text-green-200" colspan="7">
									{$i18n.t('Loading...')}
								</td>
							</tr>
						{:else if errorActivity}
							<tr>
								<td class="py-3 text-sm text-red-600 dark:text-red-400" colspan="7">
									{errorActivity}
								</td>
							</tr>
						{:else if recentActivity.length === 0}
							<tr>
								<td class="py-3 text-sm text-green-700 dark:text-green-200" colspan="7">
									{$i18n.t('No usage data')}
								</td>
							</tr>
						{:else}
							{#each recentActivity as row (row.id)}
								<tr class="border-b border-gray-100 dark:border-gray-800 last:border-0">
									<td class="py-2 text-green-900 dark:text-green-100">{row.time}</td>
									<td class="py-2 text-green-700 dark:text-green-200">
										{row.model ?? '—'}
									</td>
									<td class="py-2 text-green-700 dark:text-green-200">{row.type}</td>
									<td class="py-2 text-right text-green-700 dark:text-green-200">
										{row.input.toLocaleString()}
									</td>
									<td class="py-2 text-right text-green-700 dark:text-green-200">
										{row.output.toLocaleString()}
									</td>
									<td class="py-2 text-right text-green-900 dark:text-green-100">
										{row.total.toLocaleString()}
									</td>
									<td class="py-2 text-right">
										<button
											class="text-blue-600 dark:text-blue-400 text-xs font-medium"
											on:click={() => openDetail(row.id)}
										>
											{$i18n.t('View')}
										</button>
									</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
			<div class="mt-3 flex items-center justify-between text-xs text-green-700 dark:text-green-200">
				<div>
					{$i18n.t('Page')} {activityPage} {$i18n.t('of')} {totalPages()}
				</div>
				<div class="flex items-center gap-2">
					<button
						class="px-2 py-1 rounded-md border border-green-200/60 dark:border-green-900/50 disabled:opacity-50"
						on:click={() => goToPage(activityPage - 1)}
						disabled={activityPage <= 1 || loadingActivity}
					>
						{$i18n.t('Prev')}
					</button>
					<button
						class="px-2 py-1 rounded-md border border-green-200/60 dark:border-green-900/50 disabled:opacity-50"
						on:click={() => goToPage(activityPage + 1)}
						disabled={activityPage >= totalPages() || loadingActivity}
					>
						{$i18n.t('Next')}
					</button>
				</div>
			</div>
		</div>
	</div>

	{#if showDrawer}
		<div class="fixed inset-0 z-50">
			<div class="absolute inset-0 bg-black/30" on:click={closeDrawer}></div>
			<div
				class="absolute right-0 top-0 h-full w-full max-w-md bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 p-4"
			>
				<div class="flex items-center justify-between">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{$i18n.t('Activity Details')}
					</div>
					<button
						class="text-xs text-gray-500 dark:text-gray-400"
						on:click={closeDrawer}
					>
						{$i18n.t('Close')}
					</button>
				</div>
				<div class="mt-4 text-sm text-gray-700 dark:text-gray-200">
					{#if loadingDetail}
						<div class="h-24 rounded-lg bg-gray-100/70 dark:bg-gray-800/60 animate-pulse"></div>
					{:else if errorDetail}
						<div class="text-red-600 dark:text-red-400">{errorDetail}</div>
					{:else if activityDetail}
						<div class="flex flex-col gap-2">
							<div>
								<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('ID')}</span>
								<div>{activityDetail.id ?? selectedActivityId}</div>
							</div>
							<div>
								<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Model')}</span>
								<div>{activityDetail.model}</div>
							</div>
							<div>
								<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Type')}</span>
								<div>{activityDetail.type}</div>
							</div>
							<div>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t('Tokens')}
								</span>
								<div>
									{$i18n.t('Input')}: {activityDetail.input_tokens} · {$i18n.t('Output')}:
									{activityDetail.output_tokens} · {$i18n.t('Total')}: {activityDetail.total_tokens}
								</div>
							</div>
						</div>
					{:else}
						<div class="text-gray-500 dark:text-gray-400">
							{$i18n.t('No detail available.')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
