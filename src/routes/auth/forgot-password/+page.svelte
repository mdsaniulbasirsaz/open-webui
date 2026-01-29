<script lang="ts">
  import { getContext } from 'svelte';
  import { goto } from '$app/navigation';
  import { requestPasswordResetEmail } from '$lib/apis/auths';
  import { WEBUI_NAME } from '$lib/stores';

  const i18n = getContext('i18n');

  let email = '';
  let status: { type: 'success' | 'error' | 'info'; text: string } | null = null;
  let hasSubmitted = false;
  let loading = false;

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  $: isEmailValid = emailPattern.test(email.trim());

  const submit = async (event: Event) => {
    event.preventDefault();
    if (!isEmailValid) {
      status = {
        type: 'error',
        text: $i18n.t('Please enter a valid email address before continuing.')
      };
      return;
    }

    loading = true;
    status = null;

    try {
      const response = await requestPasswordResetEmail(email.trim());
      status = {
        type: 'success',
        text:
          response?.message ||
          $i18n.t(
            'Our backend is sending a password reset email to {{email}}. If this address is on file, check your inbox (and spam) for the link.',
            { email }
          )
      };
      hasSubmitted = true;
    } catch (err) {
      const rawError = err?.detail ?? err?.message ?? err;
      const message =
        (typeof rawError === 'string' && rawError) ||
        rawError?.message ||
        $i18n.t(
          'We could not reach the server. Please check your connection and try again.'
        );
      status = {
        type: 'error',
        text: message
      };
    } finally {
      loading = false;
    }
  };

  const handleBack = () => {
    goto('/auth');
  };
</script>

<svelte:head>
  <title>{$i18n.t('Forgot password | {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
</svelte:head>

<div class="relative min-h-screen overflow-hidden bg-transparent">
  <div class="absolute inset-0 bg-gradient-to-br from-amber-50 via-white to-sky-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-800"></div>
  <div class="absolute -top-40 -right-32 h-96 w-96 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-500/10"></div>
  <div class="absolute -bottom-40 -left-24 h-[28rem] w-[28rem] rounded-full bg-sky-300/30 blur-3xl dark:bg-sky-500/10"></div>
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.7),_transparent_55%)] dark:bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.35),_transparent_60%)]"></div>

  <div class="relative z-10 flex min-h-screen items-center justify-center px-6 py-12">
    <div class="w-full max-w-lg">
      <div class="rounded-3xl border border-white/70 bg-white/70 dark:border-white/10 dark:bg-slate-900/70 backdrop-blur-xl shadow-[0_25px_80px_-40px_rgba(15,23,42,0.6)] p-8 sm:p-10">
        <div class="space-y-2 text-center">
          <div class="text-xs uppercase tracking-[0.2em] text-[#92278F] font-bold">
            {$WEBUI_NAME}
          </div>
          <div class="text-2xl font-semibold text-slate-900 dark:text-white">
            {$i18n.t('Reset your password')}
          </div>
          <div class="text-sm font-medium text-gray-900">
            {$i18n.t('Enter the email associated with your account and we will send a reset link to that address.')}
          </div>
        </div>

        <form class="mt-6 flex flex-col gap-4" on:submit={submit}>
          <div>
            <label for="reset-email" class="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {$i18n.t('Email address')}
            </label>
            <input
              id="reset-email"
              autofocus
              required
              spellcheck="false"
              type="email"
              placeholder="email@example.com"
              bind:value={email}
              class="mt-1 w-full rounded-2xl border border-gray-700 bg-white/70 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-[rgba(146,39,143,1)] focus:outline-none focus:ring-2 focus:ring-[rgba(146,39,143,0.45)] dark:border-white/10 dark:bg-slate-950/60 dark:text-white"
              on:input={() => {
                if (status?.type === 'error') {
                  status = null;
                }
              }}
            />
          </div>

          <button
            class="w-full rounded-full bg-[#92278F] px-4 py-3 text-sm font-bold text-white "
            type="submit"
            disabled={!isEmailValid || loading}
          >
            {#if loading}
              {$i18n.t('Sending...')}
            {:else if hasSubmitted}
              {$i18n.t('Resend reset email')}
            {:else}
              {$i18n.t('Send reset email')}
            {/if}
          </button>
        </form>

        {#if status}
          <div
            class={`mt-4 rounded-2xl border p-4 text-sm ${
              status.type === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-600/60 dark:bg-emerald-900/40 dark:text-emerald-200'
                : status.type === 'error'
                ? 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-600/60 dark:bg-rose-900/40 dark:text-rose-200'
                : 'border-slate-200 bg-slate-50 text-slate-800 dark:border-white/10 dark:bg-slate-900/40 dark:text-slate-200'
            }`}
            aria-live="polite"
          >
            {status.text}
            {#if status.type === 'success'}
              <div class="mt-3 text-xs text-slate-600 dark:text-slate-300">
                {$i18n.t('Didn’t get it? Wait a minute, then try resending or check your spam folder.')}
              </div>
            {/if}
          </div>
        {/if}

        <div class="mt-6 text-center text-sm text-slate-600 dark:text-slate-300">
          <button
            type="button"
            class="font-semibold decoration-amber-400/60 bg-[#92278F] px-4 py-2 rounded-full text-white"
            on:click={handleBack}
          >
            {$i18n.t('Back to Sign in')}
          </button>
        </div>
      </div>
    </div>
  </div>
</div>
