<script lang="ts">
	import { page } from '$app/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	$: paymentId =
		$page.url.searchParams.get('paymentID') || $page.url.searchParams.get('payment_id') || '';
</script>

<svelte:head>
	<title>{$i18n.t('Payment canceled')}</title>
</svelte:head>

<div class="min-h-screen bg-white text-gray-900 flex items-center justify-center px-4 py-12">
	<div class="w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
		<div class="text-2xl font-semibold text-gray-900">{$i18n.t('Payment canceled')}</div>
		<p class="mt-2 text-sm text-gray-600">
			{$i18n.t('Your payment was canceled. You can try again anytime.')}
		</p>
		{#if paymentId}
			<div class="mt-3 text-xs text-gray-500">
				{$i18n.t('Payment ID')}: {paymentId}
			</div>
		{/if}
		<div class="mt-6 flex flex-wrap gap-2">
			<button
				class="rounded-full bg-gray-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
				type="button"
				on:click={() => {
					location.href = '/pricing';
				}}
			>
				{$i18n.t('Try again')}
			</button>
			<button
				class="rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100"
				type="button"
				on:click={() => {
					location.href = '/';
				}}
			>
				{$i18n.t('Go home')}
			</button>
		</div>
	</div>
</div>
