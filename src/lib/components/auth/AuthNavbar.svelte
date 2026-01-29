<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');
</script>

<nav class="fixed left-0 right-0 top-0 z-[100] px-4 pt-4 sm:px-8">
	<div
		class="mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-full border border-white/70 bg-white/70 px-3 py-2 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
	>
		<a
			href="/auth"
			class="flex min-w-0 items-center gap-2 rounded-full px-2 py-1 text-slate-800 transition hover:bg-white/70 dark:text-slate-100 dark:hover:bg-slate-900/40"
			data-sveltekit-preload-data="hover"
		>
			<img
				id="logo"
				crossorigin="anonymous"
				src="{WEBUI_BASE_URL}/static/logo.png"
				class="h-7 w-7 rounded-full"
				alt=""
			/>
			<span class="truncate text-sm font-semibold">{$WEBUI_NAME}</span>
		</a>

		<div class="flex items-center gap-1">
			<a
				href="/auth/home"
				class="rounded-full px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white/70 hover:text-slate-900 dark:text-slate-200 dark:hover:bg-slate-900/40 dark:hover:text-white"
				data-sveltekit-preload-data="hover"
			>
				{$i18n.t('Home')}
			</a>
			<a
				href="/auth/about"
				class="rounded-full px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white/70 hover:text-slate-900 dark:text-slate-200 dark:hover:bg-slate-900/40 dark:hover:text-white"
				data-sveltekit-preload-data="hover"
				on:click|preventDefault={() => goto('/auth/about')}
			>
				{$i18n.t('About')}
			</a>
			<a
				href="/pricing"
				class="rounded-full px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white/70 hover:text-slate-900 dark:text-slate-200 dark:hover:bg-slate-900/40 dark:hover:text-white"
				data-sveltekit-preload-data="hover"
			>
				{$i18n.t('Pricing')}
			</a>
		</div>
	</div>
</nav>
