<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';
	let updateAvailable = null;
	let version = { current: '', latest: '' };

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch(() => ({
			current: WEBUI_VERSION,
			latest: WEBUI_VERSION
		}));
		updateAvailable = compareVersion(version.latest, version.current);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch(() => '');
		if ($config?.features?.enable_version_update_check) checkForVersionUpdates();
	});
</script>

<div class="flex flex-col h-full p-6 space-y-6 bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-auto">
	<!-- Header -->
	<div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
		<div>
			<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">Synapse</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{$i18n.t('About Synapse')}</p>
		</div>

		<div class="flex flex-col md:flex-row items-start md:items-center gap-2">
			<span class="text-xs text-gray-600 dark:text-gray-400">
				<Tooltip content={WEBUI_BUILD_HASH}>
					v{WEBUI_VERSION}
				</Tooltip>
			</span>

			{#if $config?.features?.enable_version_update_check}
				<a
					href="#"
					class="text-xs font-medium text-blue-600 hover:underline pointer-events-none"
				>
					{updateAvailable === null
						? $i18n.t('Checking updates...')
						: updateAvailable
							? `(v${version.latest} ${$i18n.t('available!')})`
							: $i18n.t('(latest)')}
				</a>

				<button
					class="text-xs px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-800 dark:hover:bg-blue-700 text-blue-700 dark:text-blue-200 transition"
					on:click={checkForVersionUpdates}
				>
					{$i18n.t('Check Updates')}
				</button>
			{/if}
		</div>
	</div>

	<!-- Changelog Button -->
	<button
		class="text-xs underline text-gray-500 dark:text-gray-400 self-start"
		on:click={() => showChangelog.set(true)}
	>
		{$i18n.t("See what's new")}
	</button>

	<!-- Divider -->
	<hr class="border-gray-200 dark:border-gray-700" />

	<!-- Ollama Version -->
	{#if ollamaVersion}
		<div class="flex flex-col space-y-1">
			<h2 class="text-sm font-medium text-gray-800 dark:text-gray-200">{$i18n.t('Ollama Version')}</h2>
			<p class="text-xs text-gray-600 dark:text-gray-400">{ollamaVersion ?? 'N/A'}</p>
		</div>
		<hr class="border-gray-200 dark:border-gray-700" />
	{/if}

	<!-- License -->
	{#if $config?.license_metadata}
		<p class="text-xs text-gray-600 dark:text-gray-400">
			<span class="font-medium">{$config?.license_metadata?.organization_name}</span> - 
			<span class="capitalize">{$config?.license_metadata?.type}</span> license
		</p>
	{/if}

	<!-- Custom Footer -->
	<div class="mt-4 text-xs text-gray-700 dark:text-gray-300">
		<p>
			&copy; 2026 <span class="font-medium text-blue-600 dark:text-blue-400">bdrenai@services.bdren.net.bd</span>
		</p>
	</div>
</div>
