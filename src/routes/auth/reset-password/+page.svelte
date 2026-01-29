<script lang="ts">
  import { getContext } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { resetPasswordWithToken } from '$lib/apis/auths';
  import { WEBUI_NAME } from '$lib/stores';

  const i18n = getContext('i18n');

  let password = '';
  let confirmPassword = '';
  let showPassword = false;
  let showConfirm = false;
  let loading = false;
  let status: { type: 'success' | 'error' | 'info'; text: string } | null = null;

  let token = '';
  let emailFromUrl = '';

  // Mirror query params so the user understands which account they're updating
  $: token = $page.url.searchParams.get('token') ?? '';
  $: emailFromUrl = $page.url.searchParams.get('email') ?? '';

  const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/;

  let requirementCopy = {
    length: '',
    upper: '',
    lower: '',
    digit: '',
    symbol: ''
  };

  $: requirementCopy = {
    length: $i18n.t('At least 8 characters'),
    upper: $i18n.t('One uppercase letter'),
    lower: $i18n.t('One lowercase letter'),
    digit: $i18n.t('One number'),
    symbol: $i18n.t('One symbol (e.g. !@#$)')
  };

  $: requirements = [
    { key: 'length', met: password.length >= 8, label: requirementCopy.length },
    { key: 'upper', met: /[A-Z]/.test(password), label: requirementCopy.upper },
    { key: 'lower', met: /[a-z]/.test(password), label: requirementCopy.lower },
    { key: 'digit', met: /\d/.test(password), label: requirementCopy.digit },
    { key: 'symbol', met: /[^\w\s]/.test(password), label: requirementCopy.symbol }
  ];

  $: unmetRequirements = requirements.filter((r) => !r.met).map((r) => r.label);

  $: meetsPattern = passwordPattern.test(password);
  $: passwordsMatch = password !== '' && password === confirmPassword;
  $: canSubmit = Boolean(token) && meetsPattern && passwordsMatch && !loading;

  const handleSubmit = async (event: Event) => {
    event.preventDefault();

    if (!token) {
      status = {
        type: 'error',
        text: $i18n.t(
          'This reset link is missing a token. Request a new password reset email and try again.'
        )
      };
      return;
    }

    if (!canSubmit) {
      status = {
        type: 'error',
        text:
          unmetRequirements.length > 0
            ? $i18n.t('Missing: {{items}}', { items: unmetRequirements.join(', ') })
            : $i18n.t('Make sure your new password meets all requirements and both fields match.')
      };
      return;
    }

    loading = true;
    status = null;

    try {
      const res = await resetPasswordWithToken(token, password.trim(), emailFromUrl || undefined);
      status = {
        type: 'success',
        text:
          res?.message ||
          $i18n.t('Password updated. You can now sign in with your new credentials.')
      };
      setTimeout(() => goto('/auth'), 1200);
    } catch (err) {
      const detail = err?.detail || err?.message || '';
      status = {
        type: 'error',
        text:
          typeof detail === 'string'
            ? detail
            : detail?.message ||
              $i18n.t(
                'We could not reset your password. The link may be expired or the server is unavailable.'
              )
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
  <title>{$i18n.t('Reset password | {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
</svelte:head>

<div class="relative min-h-screen overflow-hidden bg-transparent">
  <div class="absolute inset-0 bg-gradient-to-br from-amber-50 via-white to-sky-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-800"></div>
  <div class="absolute -top-36 -right-28 h-96 w-96 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-500/10"></div>
  <div class="absolute -bottom-48 -left-20 h-[30rem] w-[30rem] rounded-full bg-sky-300/30 blur-3xl dark:bg-sky-500/10"></div>
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.7),_transparent_55%)] dark:bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.35),_transparent_60%)]"></div>

  <div class="relative z-10 flex min-h-screen items-center justify-center px-6 py-12">
    <div class="w-full max-w-2xl">
      <div class="rounded-3xl border border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-900/70 backdrop-blur-xl shadow-[0_25px_80px_-40px_rgba(15,23,42,0.6)] p-8 sm:p-10">
        <div class="flex flex-col items-center gap-3 text-center">
          <div class="space-y-2">
            <div class="text-xs uppercase font-bold text-center tracking-[0.2em] text-[#92278f]">
              {$WEBUI_NAME}
            </div>
            <div class="text-2xl font-semibold text-center text-slate-900 dark:text-white">
              {$i18n.t('Create a new password')}
            </div>
            <div class="text-sm font-medium text-slate-500 text-center dark:text-slate-400">
              {$i18n.t('Choose a strong password, confirm it, and update your account.')}
              {#if emailFromUrl}
                <span class="font-semibold text-slate-800 dark:text-slate-200">
                  {$i18n.t('Account: {{email}}', { email: emailFromUrl })}
                </span>
              {/if}
            </div>
          </div>
          <button
            type="button"
            class="text-sm font-semibold text-white bg-[#92278f] px-5 py-2 rounded-full dark:text-slate-200"
            on:click={handleBack}
          >
            {$i18n.t('Back to Sign in')}
          </button>
        </div>

        <form class="mt-8 grid gap-6 md:grid-cols-2" on:submit={handleSubmit}>
          <div class="md:col-span-2 grid gap-4">
            <label class="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {$i18n.t('New password')}
            </label>
            <div class="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                autocomplete="new-password"
                spellcheck="false"
                placeholder={$i18n.t('Enter a strong password')}
                bind:value={password}
                class="w-full rounded-full border border-slate-400 bg-white/80 px-4 py-3 pr-12 text-sm text-slate-900 placeholder:text-slate-500 focus:border-[rgba(146,39,143,1)] focus:outline-none focus:ring-2 focus:ring-[rgba(146,39,143,0.45)] dark:border-white/10 dark:bg-slate-950/60 dark:text-white"
                on:input={() => {
                  if (status?.type === 'error') status = null;
                }}
              />
              <button
                type="button"
                class="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-slate-600 hover:text-slate-800 dark:text-slate-300 dark:hover:text-white"
                on:click={() => (showPassword = !showPassword)}
              >
                {showPassword ? $i18n.t('Hide') : $i18n.t('Show')}
              </button>
            </div>
          </div>

          <div class="md:col-span-2 grid gap-4">
            <label class="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {$i18n.t('Confirm password')}
            </label>
            <div class="relative">
              <input
                type={showConfirm ? 'text' : 'password'}
                required
                autocomplete="new-password"
                spellcheck="false"
                placeholder={$i18n.t('Re-enter the same password')}
                bind:value={confirmPassword}
                class={`w-full rounded-full border px-4 py-3 pr-12 text-sm text-slate-900  placeholder:text-slate-500 focus:outline-none focus:ring-2 ${
                  passwordsMatch || confirmPassword === ''
                    ? 'border-slate-400 bg-white/80 focus:border-[rgba(146,39,143,1)] focus:ring-[rgba(146,39,143,0.45)] dark:border-white/10 dark:bg-slate-950/60 dark:text-white'
                    : 'border-rose-400 bg-rose-50/70 focus:border-rose-400 focus:ring-rose-300/60 dark:border-rose-500/60 dark:bg-rose-900/50 dark:text-rose-50'
                }`}
                on:input={() => {
                  if (status?.type === 'error') status = null;
                }}
              />
              <button
                type="button"
                class="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-slate-600 hover:text-slate-800 dark:text-slate-300 dark:hover:text-white"
                on:click={() => (showConfirm = !showConfirm)}
              >
                {showConfirm ? $i18n.t('Hide') : $i18n.t('Show')}
              </button>
            </div>
            {#if confirmPassword !== '' && !passwordsMatch}
              <div class="text-xs font-medium text-rose-600 dark:text-rose-300">
                {$i18n.t("The passwords you entered don't match.")}
              </div>
            {/if}
          </div>

          <div class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 text-sm dark:border-white/10 dark:bg-slate-900/50 md:col-span-2">
            <div class="font-semibold text-slate-800 dark:text-slate-100">
              {$i18n.t('Password strength')}
            </div>
            <div class="mt-2 grid gap-2 sm:grid-cols-2">
              {#each requirements as requirement}
                <div class="flex items-center gap-2 rounded-xl bg-white/70 px-3 py-2 text-slate-700 shadow-[0_8px_20px_-15px_rgba(15,23,42,0.45)] dark:bg-slate-950/60 dark:text-slate-200">
                  <span
                    class={`h-2 w-2 rounded-full ${
                      requirement.met ? 'bg-emerald-500 ring-2 ring-emerald-200/60' : 'bg-slate-300 ring-2 ring-transparent dark:bg-slate-600'
                    }`}
                  ></span>
                  <span class={requirement.met ? 'font-semibold text-slate-900 dark:text-white' : ''}>
                    {requirement.label}
                  </span>
                </div>
              {/each}
            </div>
            {#if !meetsPattern}
              <div class="mt-3 text-xs text-rose-600 dark:text-rose-300">
                {$i18n.t('Password must include:')} {unmetRequirements.join(', ')}
              </div>
            {:else}
              <div class="mt-3 text-xs text-emerald-700 dark:text-emerald-300">
                {$i18n.t('Looking good. Keep this password private!')}
              </div>
            {/if}
          </div>

          <div class="md:col-span-2">
            <button
              class="w-full rounded-full bg-[#92278f] px-4 py-3 text-sm font-semibold text-white shadow-lg  transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900 disabled:cursor-not-allowed"
              type="submit"
              disabled={!canSubmit}
            >
              {#if loading}
                {$i18n.t('Updating...')}
              {:else}
                {$i18n.t('Update password')}
              {/if}
            </button>
          </div>
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
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
