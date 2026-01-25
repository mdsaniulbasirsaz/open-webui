<script lang="ts">
	import { page } from '$app/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	$: paymentId =
		$page.url.searchParams.get('paymentID') ||
		$page.url.searchParams.get('payment_id') ||
		'';
</script>

<svelte:head>
	<title>{$i18n.t('Payment canceled')}</title>
</svelte:head>

<main class="flex items-center justify-center min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 px-4">
	<section
		class="w-full max-w-2xl p-12 text-center bg-white shadow-lg rounded-xl transition-shadow hover:shadow-xl"
	>
		<!-- Canceled Icon -->
		<div class="flex items-center justify-center w-24 h-24 mx-auto mb-8 bg-amber-100 rounded-full">
			<svg
				class="w-12 h-12 text-amber-600"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				stroke-width="2"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M12 9v2m0 4h.01M10.29 3.86l-7.4 12.82A2 2 0 004.6 19h14.8a2 2 0 001.71-2.32l-7.4-12.82a2 2 0 00-3.42 0z"
				/>
			</svg>
		</div>

		<!-- Main Content -->
		<h1 class="mb-6 text-3xl font-extrabold text-amber-600">
			{$i18n.t('Payment canceled')}
		</h1>

		<p class="mb-8 text-md text-gray-700">
			{$i18n.t('Your payment was canceled. You can try again anytime.')}
		</p>

		<!-- Highlighted Info -->
		<div class="p-6 mb-8 rounded-lg bg-amber-50">
			<p class="text-lg font-medium text-amber-700">
				{$i18n.t('No charges were made to your account.')}
			</p>

			{#if paymentId}
				<p class="mt-2 text-sm font-mono text-amber-600">
					{$i18n.t('Payment ID')}: {paymentId}
				</p>
			{/if}
		</div>

		<!-- Support Section -->
		<div class="pt-8 mt-8 border-t border-gray-100">
			<p class="text-lg text-gray-700">
				{$i18n.t('Need help? Contact us at')}
			</p>
			<a
				href="mailto:admin@eliteai.tools"
				class="inline-block mt-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
			>
				bdrenai@services.bdren.net.bd
			</a>
		</div>

		<!-- CTA -->
		<div class="mt-12 flex flex-col sm:flex-row justify-center gap-4">
			<button
				class="px-12 py-3 text-sm font-semibold text-white bg-amber-600 rounded-full hover:bg-amber-700 transition-colors"
				type="button"
				on:click={() => (location.href = '/pricing')}
			>
				{$i18n.t('Try again')}
			</button>

			<button
				class="px-8 py-3 text-sm font-semibold text-gray-700 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"
				type="button"
				on:click={() => (location.href = '/pricing')}
			>
				{$i18n.t('Back to pricing')}
			</button>
		</div>
	</section>
</main>
