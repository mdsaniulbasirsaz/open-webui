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
	<title>{$i18n.t('Payment successful')}</title>
</svelte:head>

<main class="flex items-center justify-center min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 px-4">
	<section
		class="w-full max-w-2xl p-12 text-center bg-white shadow-lg rounded-xl transition-shadow hover:shadow-xl"
	>
		<!-- Success Icon -->
		<div class="flex items-center justify-center w-24 h-24 mx-auto mb-8 bg-green-100 rounded-full">
			<svg
				class="w-12 h-12 text-green-600"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				stroke-width="2"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
			</svg>
		</div>

		<!-- Main Content -->
		<h1 class="mb-6 text-3xl font-extrabold text-green-600">
			{$i18n.t('Payment successful!')}
		</h1>

		<p class="mb-8 text-md text-gray-700">
			{$i18n.t('Thank you for your purchase.')}
		</p>

		<!-- Highlighted Info -->
		<div class="p-6 mb-8 rounded-lg bg-blue-50">
			<p class="text-lg font-medium text-blue-700">
				{$i18n.t('Your subscription is now active and will be reflected shortly.')}
			</p>
			{#if paymentId}
				<p class="mt-2 text-sm text-blue-600 font-mono">
					{$i18n.t('Payment ID')}: {paymentId}
				</p>
			{/if}
		</div>

		<!-- Contact Section -->
		<div class="pt-8 mt-8 border-t border-gray-100">
			<p class="text-lg text-gray-700">
				{$i18n.t('Have questions? Contact us at')}
			</p>
			<a
				href="mailto:admin@eliteai.tools"
				class="inline-block mt-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
			>
				bdrenai@services.bdren.net.bd
			</a>
		</div>

		<!-- CTA -->
		<div class="mt-12">
			<button
				class="inline-block px-5 py-3 text-sm font-semibold text-white rounded-full transition-colors hover:opacity-90"
				style="background-color: rgba(146, 39, 143);"
				type="button"
				on:click={() => (location.href = '/pricing')}
			>
				{$i18n.t('View Another Plans')}
			</button>
		</div>
	</section>
</main>
