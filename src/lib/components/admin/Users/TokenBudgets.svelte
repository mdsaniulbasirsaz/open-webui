<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import dayjs from 'dayjs';
	import utc from 'dayjs/plugin/utc';
	import { toast } from 'svelte-sonner';

	import {
		getUserTokenBudgetStatus,
		upsertUserTokenBudget,
		type TokenBudgetStatus
	} from '$lib/apis/token_budgets';
	import { searchUsers } from '$lib/apis/users';

	const i18n = getContext('i18n');
	dayjs.extend(utc);

	let userId = '';
	let timezone = 'UTC';
	let enabled = true;
	let limitTokens: number | '' = '';

	type UserSearchItem = {
		id: string;
		email?: string | null;
		name?: string | null;
	};

	let userSearch = '';
	let userSearchOpen = false;
	let userSearchLoading = false;
	let userSearchResults: UserSearchItem[] = [];
	let userSearchSelected: UserSearchItem | null = null;
	let userSearchDebounce: ReturnType<typeof setTimeout> | null = null;
	let userSearchContainer: HTMLDivElement | null = null;

	onMount(() => {
		const onPointerDown = (e: PointerEvent) => {
			if (!userSearchOpen) return;
			const target = e.target as Node | null;
			if (!target) return;
			if (!userSearchContainer?.contains(target)) {
				// Defer closing so we don't interrupt the native click/toggle on the actual target
				// (e.g. the Enabled checkbox) during the same pointer event.
				setTimeout(() => {
					userSearchOpen = false;
				}, 0);
			}
		};

		document.addEventListener('pointerdown', onPointerDown, true);

		return () => {
			document.removeEventListener('pointerdown', onPointerDown, true);
		};
	});

	onDestroy(() => {
		if (userSearchDebounce) clearTimeout(userSearchDebounce);
	});

	let status: TokenBudgetStatus | null = null;
	let loadingStatus = false;
	let saving = false;

	$: usedTokens = status?.used_tokens ?? 0;
	$: reservedTokens = status?.reserved_tokens ?? 0;
	$: remainingTokens = status?.remaining_tokens ?? 0;
	$: limitTokensStatus = status?.limit_tokens ?? 0;
	$: usagePercent =
		limitTokensStatus > 0
			? Math.min(100, Math.max(0, Math.round((usedTokens / limitTokensStatus) * 100)))
			: 0;
	$: reservedPercent =
		limitTokensStatus > 0
			? Math.min(100, Math.max(0, Math.round((reservedTokens / limitTokensStatus) * 100)))
			: 0;

	const clearSelectedUser = () => {
		userId = '';
		userSearchSelected = null;
		userSearch = '';
		status = null;
	};

	const runUserSearch = async () => {
		const q = userSearch.trim();
		if (q.length < 2) {
			userSearchResults = [];
			userSearchOpen = false;
			return;
		}

		userSearchLoading = true;
		try {
			const res = await searchUsers(localStorage.token, q, 'created_at', 'desc', 1);
			const users = (res?.users ?? []) as UserSearchItem[];
			userSearchResults = users.slice(0, 8);
			userSearchOpen = true;
		} catch (err) {
			userSearchResults = [];
			userSearchOpen = false;
			toast.error(`${err}`);
		} finally {
			userSearchLoading = false;
		}
	};

	const onUserSearchInput = () => {
		userSearchSelected = null;
		userId = '';
		status = null;

		if (userSearchDebounce) clearTimeout(userSearchDebounce);
		userSearchDebounce = setTimeout(() => {
			runUserSearch();
		}, 250);
	};

	const selectUser = (u: UserSearchItem) => {
		userSearchSelected = u;
		userId = u.id;
		userSearch = u.email || u.name || u.id;
		userSearchOpen = false;
		userSearchResults = [];
	};

	const loadStatus = async () => {
		const trimmed = userId.trim();
		if (!trimmed) {
			toast.error($i18n.t('Please select a user.'));
			return;
		}

		loadingStatus = true;
		try {
			const res = await getUserTokenBudgetStatus(localStorage.token, trimmed);
			status = res;
			timezone = res.timezone ?? timezone;
			enabled = res.enabled;
			limitTokens = res.limit_tokens;
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			loadingStatus = false;
		}
	};

	const saveBudget = async () => {
		const trimmed = userId.trim();
		if (!trimmed) {
			toast.error($i18n.t('Please select a user.'));
			return;
		}
		const numericLimit = typeof limitTokens === 'number' ? limitTokens : Number(limitTokens);
		if (!Number.isFinite(numericLimit) || numericLimit < 0) {
			toast.error($i18n.t('Monthly token limit must be a number >= 0.'));
			return;
		}

		saving = true;
		try {
			await upsertUserTokenBudget(localStorage.token, trimmed, {
				limit_tokens: numericLimit,
				enabled,
				timezone: timezone?.trim() || null
			});
			toast.success($i18n.t('Saved.'));
			await loadStatus();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			saving = false;
		}
	};

	const formatDateTime = (epoch: number) => {
		if (!epoch) return '-';
		return dayjs(epoch * 1000)
			.utc()
			.format('YYYY-MM-DD HH:mm:ss [UTC]');
	};
</script>

<div class="w-full max-w-4xl">
	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0">
			<div class="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
				{$i18n.t('Token Budgets')}
			</div>
			<div class="mt-1 text-sm text-gray-600 dark:text-gray-300">
				{$i18n.t('Set a monthly token limit per user and view remaining budget.')}
			</div>
		</div>
	</div>

	<div
		class="mt-4 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-sm"
	>
		<div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
			<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Configuration')}
			</div>
			<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t(
					'Search a user by email, adjust the monthly limit, then save. Use "Load status" to verify the current window.'
				)}
			</div>
		</div>

		<div class="p-5">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-800 dark:text-gray-200"
						>{$i18n.t('User ID')}</label
					>
					<div class="relative" bind:this={userSearchContainer}>
						<input
							class="w-full px-3 py-2.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition pr-10"
							placeholder={$i18n.t('Search by email (or name)…')}
							bind:value={userSearch}
							autocomplete="off"
							on:input={onUserSearchInput}
							on:focus={() => {
								if (userSearchResults.length > 0) userSearchOpen = true;
							}}
						/>

						{#if userSearchLoading}
							<div class="absolute right-3 top-1/2 -translate-y-1/2">
								<span
									class="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-transparent animate-spin"
								/>
							</div>
						{:else if userSearchSelected || userSearch}
							<button
								type="button"
								class="absolute right-2.5 top-1/2 -translate-y-1/2 h-6 w-6 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								on:click={clearSelectedUser}
								aria-label={$i18n.t('Clear')}
							>
								<span class="text-lg leading-none">×</span>
							</button>
						{/if}

						{#if userSearchOpen && userSearchResults.length > 0}
							<div
								class="absolute z-20 mt-2 w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg overflow-hidden"
							>
								{#each userSearchResults as u (u.id)}
									<button
										type="button"
										class="w-full text-left px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
										on:click={() => selectUser(u)}
									>
										<div class="flex items-start justify-between gap-3">
											<div class="min-w-0">
												<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
													{u.email || u.name || u.id}
												</div>
												<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 truncate">
													{u.name ? u.name : $i18n.t('No name')} · {u.id}
												</div>
											</div>
											<div
												class="shrink-0 text-xs font-medium text-emerald-700 dark:text-emerald-300"
											>
												{$i18n.t('Select')}
											</div>
										</div>
									</button>
								{/each}
							</div>
						{:else if userSearchOpen && !userSearchLoading && userSearch.trim().length >= 2}
							<div
								class="absolute z-20 mt-2 w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg px-3 py-2.5 text-sm text-gray-600 dark:text-gray-300"
							>
								{$i18n.t('No users found.')}
							</div>
						{/if}
					</div>

					{#if userSearchSelected}
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Selected')}:
							<span class="font-medium text-gray-800 dark:text-gray-200">
								{userSearchSelected.email || userSearchSelected.name || userSearchSelected.id}
							</span>
							· <span class="font-mono">{userSearchSelected.id}</span>
						</div>
					{:else}
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Search results include email, name, and user id. Select one to continue.')}
						</div>
					{/if}
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-800 dark:text-gray-200"
						>{$i18n.t('Timezone')}</label
					>
					<input
						class="w-full px-3 py-2.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition"
						placeholder="UTC"
						bind:value={timezone}
					/>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Used for monthly window boundaries.')}
					</div>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-800 dark:text-gray-200"
						>{$i18n.t('Monthly token limit')}</label
					>
					<input
						type="number"
						min="0"
						class="w-full px-3 py-2.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition"
						bind:value={limitTokens}
					/>
					
				</div>

					<div class="flex flex-col gap-2">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<div class="text-sm font-medium text-gray-800 dark:text-gray-200">
									{$i18n.t('Token Limit Enable or Disabled')}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t('Controls whether this user is subject to the monthly token limit.')}
								</div>
							</div>
							<div class="text-xs font-medium text-gray-700 dark:text-gray-300 shrink-0">
								{#if enabled}
									{$i18n.t('Enabled')}
								{:else}
									{$i18n.t('Disabled')}
								{/if}
							</div>
						</div>

						<div
							class="grid grid-cols-2 w-full sm:w-max rounded-xl p-1 border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900"
							role="group"
							aria-label={$i18n.t('Token limit enable or disabled')}
						>
							<label
								class={`cursor-pointer select-none px-4 py-2 rounded-lg text-sm font-medium text-center transition ${
									enabled
										? 'bg-emerald-600 text-white shadow-sm'
										: 'text-gray-700 dark:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-850'
								}`}
							>
								<input
									class="sr-only"
									type="radio"
									name="token-budget-enabled"
									value={true}
									bind:group={enabled}
								/>
								{$i18n.t('Enabled')}
							</label>
							<label
								class={`cursor-pointer select-none px-4 py-2 rounded-lg text-sm font-medium text-center transition ${
									!enabled
										? 'bg-gray-900 text-white dark:bg-gray-700 shadow-sm'
										: 'text-gray-700 dark:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-850'
								}`}
							>
								<input
									class="sr-only"
									type="radio"
									name="token-budget-enabled"
									value={false}
									bind:group={enabled}
								/>
								{$i18n.t('Disabled')}
							</label>
						</div>
					</div>

			</div>

			<div class="mt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Tip: Load status after saving to confirm remaining budget updates.')}
				</div>

				<div class="flex items-center justify-end gap-2">
					<button
						class="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-sm font-medium border border-gray-200 dark:border-gray-700 bg-gray-200 dark:bg-gray-900 text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60 disabled:cursor-not-allowed transition"
						on:click={loadStatus}
						disabled={loadingStatus || saving}
					>
						{#if loadingStatus}
							<span
								class="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-transparent animate-spin"
							/>
							{$i18n.t('Loading...')}
						{:else}
							{$i18n.t('Load status')}
						{/if}
					</button>
					<button
						class="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-sm transition"
						on:click={saveBudget}
						disabled={saving || loadingStatus}
					>
						{#if saving}
							<span
								class="h-4 w-4 rounded-full border-2 border-emerald-200 border-t-transparent animate-spin"
							/>
							{$i18n.t('Saving...')}
						{:else}
							{$i18n.t('Save')}
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>

	{#if status}
		<div
			class="mt-4 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-sm overflow-hidden"
		>
			<div
				class="px-5 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between gap-3"
			>
				<div class="min-w-0">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{$i18n.t('Current status')}
					</div>
					<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Timestamps are shown in UTC.')}
					</div>
				</div>
				{#if limitTokensStatus > 0}
					<div class="shrink-0 text-xs font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Used')}
						{usagePercent}%
					</div>
				{/if}
			</div>

			<div class="p-5">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Window start')}
						</div>
						<div class="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
							{formatDateTime(status.window_start)}
						</div>
					</div>
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Resets at')}
						</div>
						<div class="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
							{formatDateTime(status.reset_at)}
						</div>
					</div>
				</div>

				{#if limitTokensStatus > 0}
					<div class="mt-4">
						<div class="h-2.5 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
							<div class="h-full bg-emerald-600" style={`width: ${usagePercent}%`} />
						</div>
						<div
							class="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400"
						>
							<div>
								{$i18n.t('Used')}
								{usedTokens} ({usagePercent}%)
							</div>
							<div>
								{$i18n.t('Limit')}
								{limitTokensStatus}
							</div>
						</div>
					</div>
				{/if}

				<div class="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Remaining')}
						</div>
						<div class="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
							{remainingTokens}
						</div>
					</div>
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Used')}
						</div>
						<div class="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
							{usedTokens}
						</div>
					</div>
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Reserved')}
						</div>
						<div class="mt-1 flex items-baseline gap-2">
							<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
								{reservedTokens}
							</div>
							{#if limitTokensStatus > 0 && reservedTokens > 0}
								<div class="text-xs font-medium text-amber-700 dark:text-amber-300">
									{reservedPercent}%
								</div>
							{/if}
						</div>
					</div>
					<div
						class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
					>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Limit')}
						</div>
						<div class="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
							{#if limitTokensStatus > 0}
								{limitTokensStatus}
							{:else}
								{$i18n.t('No limit')}
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
