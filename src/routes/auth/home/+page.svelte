<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME } from '$lib/stores';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';

	const i18n = getContext('i18n');

	const sections = {
		featureCards: [
			{
				Icon: Sparkles,
				title: 'Clean workflow',
				description: 'Stay focused with a UI that highlights what matters.'
			},
			{
				Icon: LockClosed,
				title: 'Privacy & security',
				description: 'Thoughtful defaults to help protect your workspace.'
			},
			{
				Icon: Bolt,
				title: 'Fast iterations',
				description: 'Move from idea to outcome without friction.'
			},
			{
				Icon: UserGroup,
				title: 'Team-ready',
				description: 'Share context, collaborate, and keep everyone aligned.'
			},
			{
				Icon: Cloud,
				title: 'Available anywhere',
				description: 'Access Synapse across devices and environments.'
			},
			{
				Icon: ChartBar,
				title: 'Measure progress',
				description: 'Simple insights that help you improve the workflow.'
			}
		],
		useCaseCards: [
			{
				title: 'Knowledge hub',
				description: 'Organize notes, decisions, and references in one place.'
			},
			{
				title: 'Project execution',
				description: 'Turn requirements into tasks and keep delivery on track.'
			},
			{
				title: 'Support workflows',
				description: 'Capture context quickly and respond with consistency.'
			},
			{
				title: 'Team onboarding',
				description: 'Help new teammates ramp up with shared context.'
			}
		]
	};

	// Function to generate a random color
	function getRandomColor() {
		const hue = Math.floor(Math.random() * 360);
		const saturation = 60;
		const lightness = 92;

		return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
	}

	// Generate a random color for each item in featureCards
	let featureCards = sections.featureCards.map(item => ({
		...item,
		bgColor: getRandomColor()
	}));


	let useCaseCards = sections.useCaseCards.map(item => ({
		...item,
		bgColor: getRandomColor()
	}));

</script>

<svelte:head>
	<title>{$i18n.t('Home | {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
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

	<div class="relative mx-auto flex min-h-screen w-full flex-col px-6 pb-16 pt-28 sm:px-8 lg:px-12">
		<!-- Hero -->
		<section class="mx-auto w-full max-w-6xl text-center">
			<div
				class="inline-flex items-center justify-center rounded-full border border-white/70 bg-white/70 px-4 py-2 text-xs font-semibold text-slate-700 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:text-slate-200 dark:ring-white/10"
			>
				<span class="text-[#92278F]">Synapse</span>
				<span class="mx-2 opacity-50">•</span>
				<span>{$i18n.t('Your workspace, connected.')}</span>
			</div>

			<h1
				class="mt-6 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white"
			>
				{$i18n.t('Build, Chat and Ship faster with Synapse.')}
			</h1>
			<p
				class="mx-auto mt-5 max-w-prose text-sm font-medium text-slate-600 dark:text-slate-300 sm:text-base"
			>
				{$i18n.t(
					'Synapse brings conversations, knowledge, and tools into one clear workflow so your team can move with confidence.'
				)}
			</p>

			<div class="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
				<a
					href="/auth"
					data-sveltekit-preload-data="hover"
					class="inline-flex w-full items-center justify-center rounded-full bg-[#92278F] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-[rgba(146,39,143,0.35)] transition hover:brightness-110 sm:w-auto"
				>
					{$i18n.t('Sign in')}
				</a>
				<a
					href="/auth?mode=signup"
					data-sveltekit-preload-data="hover"
					class="inline-flex w-full items-center justify-center rounded-full border border-slate-200/80 bg-white/70 px-6 py-3 text-sm font-semibold text-slate-800 transition hover:bg-white dark:border-white/10 dark:bg-slate-950/40 dark:text-slate-100 dark:hover:bg-slate-900/60 sm:w-auto"
				>
					{$i18n.t('Create account')}
				</a>
			</div>
		</section>

		<!-- About (Synapse) -->
		<section class="mx-auto mt-12 w-full max-w-7xl">
			<div
				class="rounded-2xl border border-white/70 bg-white/70 p-8 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
			>
				<h2 class="text-2xl text-center font-bold text-[#92278F] dark:text-white">
					{$i18n.t('About Synapse')}
				</h2>
				<p class="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300 sm:text-base">
					{$i18n.t(
						'Synapse is designed to connect people, context, and outcomes. It helps you keep knowledge organized, reduce repeated work, and turn ideas into action with a clean, secure, and collaborative experience.'
					)}
				</p>

				<div class="mt-6 grid gap-4 sm:grid-cols-3">
					<div
						class="rounded-xl border border-white/70 bg-green-400/20 p-4 dark:border-white/10 dark:bg-slate-950/30"
					>
						<div class="text-sm text-center font-semibold text-slate-900 dark:text-white">
							{$i18n.t('Clarity')}
						</div>
						<div class="mt-1 text-xs text-center text-slate-600 dark:text-slate-300">
							{$i18n.t('Keep your workspace easy to navigate.')}
						</div>
					</div>
					<div
						class="rounded-xl border border-white/70 bg-yellow-300/20 p-4 dark:border-white/10 dark:bg-slate-950/30"
					>
						<div class="text-sm text-center font-semibold text-slate-900 dark:text-white">
							{$i18n.t('Security')}
						</div>
						<div class="mt-1 text-xs text-center text-slate-600 dark:text-slate-300">
							{$i18n.t('Protect data with thoughtful defaults.')}
						</div>
					</div>
					<div
						class="rounded-xl border border-white/70 bg-blue-400/20 p-4 dark:border-white/10 dark:bg-slate-950/30"
					>
						<div class="text-sm text-center font-semibold text-slate-900 dark:text-white">
							{$i18n.t('Momentum')}
						</div>
						<div class="mt-1 text-xs text-center text-slate-600 dark:text-slate-300">
							{$i18n.t('Move from idea to result faster.')}
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Card Grid Sections -->
		<section class="mx-auto mt-12 w-full max-w-7xl">
			<div class="text-center">
				<h2 class="text-2xl font-bold text-[#92278F] dark:text-white">
					{$i18n.t('Why teams choose Synapse')}
				</h2>
				<p class="mx-auto mt-3 max-w-prose text-sm text-slate-600 dark:text-slate-300 sm:text-base">
					{$i18n.t('A few highlights that make the experience feel fast, calm, and reliable.')}
				</p>
			</div>

			<div class="mt-6 grid gap-6 sm:grid-cols-2">
				{#each featureCards as item (item.title)}
					<div
					class="rounded-2xl border border-white/70 p-6 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
					style="background-color: {item.bgColor}"
					>
					<div class="flex h-10 w-10 items-center justify-center rounded-xl bg-[#92278F]/10 text-[#92278F] dark:bg-[#92278F]/15">
						<svelte:component this={item.Icon} class="h-5 w-5" />
					</div>
					<div class="mt-4 text-base font-semibold text-slate-900 dark:text-white">
						{$i18n.t(item.title)}
					</div>
					<p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
						{$i18n.t(item.description)}
					</p>
					</div>
				{/each}
			</div>
		</section>

		<section class="mx-auto mt-12 w-full max-w-7xl">
			<div
				class="rounded-2xl border border-white/70 bg-white/70 p-8 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
			>
				<h2 class="text-2xl font-bold text-center text-[#92278F] dark:text-white">
					{$i18n.t('What you can do')}
				</h2>
				<p class="mt-3 text-sm text-center text-slate-600 dark:text-slate-300 sm:text-base">
					{$i18n.t('Use Synapse as a flexible foundation for your team’s day-to-day work.')}
				</p>

				<div class="mt-6 grid gap-4 sm:grid-cols-2">
					{#each useCaseCards as card (card.title)}
						<div
							class="rounded-xl border border-white/70 bg-white/60 p-5 dark:border-white/10 dark:bg-slate-950/30"
							style="background-color: {card.bgColor}"
						>
							<div class="text-sm font-semibold text-slate-900 dark:text-white">
								{$i18n.t(card.title)}
							</div>
							<div class="mt-1 text-xs text-slate-600 dark:text-slate-300">
								{$i18n.t(card.description)}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Footer -->
		<footer class="mx-auto mt-12 w-full max-w-7xl pb-6">
			<div
				class="rounded-2xl border border-white/70 bg-white/70 p-6 shadow-lg shadow-slate-900/10 ring-1 ring-white/70 backdrop-blur dark:border-white/10 dark:bg-slate-950/40 dark:ring-white/10"
			>
				<div class="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
					<div class="flex items-center gap-3">
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/logo.png"
							alt=""
							class="h-9 w-9 rounded-full"
						/>
						<div class="min-w-0">
							<div class="truncate text-sm font-semibold text-slate-900 dark:text-white">
								{$WEBUI_NAME}
							</div>
							<div class="text-xs text-slate-600 dark:text-slate-300">
								{$i18n.t('Synapse workspace')}
							</div>
						</div>
					</div>

					<nav class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
						<a
							href="/auth"
							data-sveltekit-preload-data="hover"
							class="text-slate-700 transition hover:text-slate-900 dark:text-slate-200 dark:hover:text-white"
							>{$i18n.t('Sign in')}</a
						>
						<a
							href="/auth?mode=signup"
							data-sveltekit-preload-data="hover"
							class="text-slate-700 transition hover:text-slate-900 dark:text-slate-200 dark:hover:text-white"
							>{$i18n.t('Sign up')}</a
						>
						<a
							href="/pricing"
							data-sveltekit-preload-data="hover"
							class="text-slate-700 transition hover:text-slate-900 dark:text-slate-200 dark:hover:text-white"
							>{$i18n.t('Pricing')}</a
						>
						<a
							href="/terms"
							data-sveltekit-preload-data="hover"
							class="text-slate-700 transition hover:text-slate-900 dark:text-slate-200 dark:hover:text-white"
							>{$i18n.t('Terms and conditions')}</a
						>
						<a
							href="/auth/about"
							data-sveltekit-preload-data="hover"
							class="text-slate-700 transition hover:text-slate-900 dark:text-slate-200 dark:hover:text-white"
							>{$i18n.t('About')}</a
						>
					</nav>
				</div>

				<div
					class="mt-6 border-t border-slate-200/70 pt-4 text-xs text-slate-500 dark:border-white/10 dark:text-slate-400"
				>
					{$i18n.t('© {{year}} {{WEBUI_NAME}}. All rights reserved. Email: bdrenai@services.net.bd', {
						year: new Date().getFullYear(),
						WEBUI_NAME: $WEBUI_NAME
					})}
				</div>
			</div>
		</footer>
	</div>
</div>
