<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';

	const i18n = getContext('i18n');

	const highlights = [
		{
			Icon: Sparkles,
			title: 'Clean, modern experience',
			description: 'A focused interface that stays out of your way while you work.'
		},
		{
			Icon: LockClosed,
			title: 'Security-minded by default',
			description: 'Designed to help protect your workspace and user data.'
		},
		{
			Icon: Bolt,
			title: 'Fast to start, easy to extend',
			description: 'Quick setup today, flexible enough for tomorrow’s workflows.'
		},
		{
			Icon: UserGroup,
			title: 'Built for teams',
			description: 'Share context, collaborate, and keep everyone aligned.'
		},
		{
			Icon: Cloud,
			title: 'Access anywhere',
			description: 'Pick up where you left off across devices and environments.'
		},
		{
			Icon: ChartBar,
			title: 'Track what matters',
			description: 'See activity and outcomes with simple, useful insights.'
		}
	];
</script>

<svelte:head>
	<title>{$i18n.t('About | {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
</svelte:head>

<div
	class="relative h-[100dvh] overflow-y-auto overscroll-contain overflow-x-hidden bg-gradient-to-br from-amber-50 via-white to-sky-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-800"
>
	<div class="pointer-events-none absolute inset-0">
		<div
			class="absolute -left-24 -top-24 h-[30rem] w-[30rem] rounded-full bg-amber-300/35 blur-3xl dark:bg-amber-500/10"
		></div>
		<div
			class="absolute -right-24 -bottom-24 h-[30rem] w-[30rem] rounded-full bg-sky-300/35 blur-3xl dark:bg-sky-500/10"
		></div>
		<div
			class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.7),_transparent_55%)] dark:bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.35),_transparent_60%)]"
		></div>
	</div>

	<div class="relative mx-auto flex min-h-screen max-w-6xl flex-col px-6 pb-16 pt-28 sm:px-8">
		<header class="mx-auto w-full max-w-3xl text-center">
			<div class="text-xs font-bold uppercase tracking-[0.2em] text-[#92278F]">
				{$WEBUI_NAME}
			</div>
			<h1 class="mt-3 text-4xl font-semibold text-[#92278F] dark:text-white sm:text-5xl">
				{$i18n.t('About')}
			</h1>
			<p class="mx-auto mt-4 max-w-prose text-sm font-medium text-slate-600 dark:text-slate-300">
				{$i18n.t('A quick overview of this workspace and what you can do next.')}
			</p>
		</header>

		<main class="mx-auto mt-12 w-full max-w-4xl">
			<section>
				<div class="grid gap-6 sm:grid-cols-2">
					{#each highlights as item (item.title)}
						<div
							class="rounded-2xl border border-white/70 bg-white/70 p-6 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
						>
							<div
								class="flex h-10 w-10 items-center justify-center rounded-xl bg-[#92278F]/10 text-[#92278F] dark:bg-[#92278F]/15"
							>
								<svelte:component this={item.Icon} class="h-5 w-5" />
							</div>
							<h2 class="mt-4 text-base font-semibold text-slate-900 dark:text-white">
								{$i18n.t(item.title)}
							</h2>
							<p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
								{$i18n.t(item.description)}
							</p>
						</div>
					{/each}
				</div>

				<div
					class="mt-6 rounded-2xl border border-white/70 bg-white/70 p-6 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
				>
					<h2 class="text-base font-semibold text-slate-900 dark:text-white">
						{$i18n.t('Get started in a few steps')}
					</h2>
					<ul class="mt-4 space-y-3 text-sm text-slate-700 dark:text-slate-200">
						<li class="flex gap-3">
							<span class="mt-1 inline-block h-2 w-2 shrink-0 rounded-full bg-[#92278F]/70"></span>
							<span>{$i18n.t('Sign in to access your workspace and settings.')}</span>
						</li>
						<li class="flex gap-3">
							<span class="mt-1 inline-block h-2 w-2 shrink-0 rounded-full bg-[#92278F]/70"></span>
							<span>{$i18n.t('Explore pricing plans if you need advanced features.')}</span>
						</li>
						<li class="flex gap-3">
							<span class="mt-1 inline-block h-2 w-2 shrink-0 rounded-full bg-[#92278F]/70"></span>
							<span>{$i18n.t('Return home anytime to continue your work.')}</span>
						</li>
					</ul>
				</div>
			</section>
		</main>
	</div>
</div>
