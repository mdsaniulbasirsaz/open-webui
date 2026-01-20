<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
	const currentYear = new Date().getFullYear();

	const personalPlans = [
		{
			name: 'Free',
			tagline: 'Intelligence for everyday tasks',
			price: '$0',
			period: '/ month',
			cta: 'Get Free',
			featured: false,
			note: '',
			features: [
				'Limited access to flagship model GPT-5.2',
				'Limited messages and uploads',
				'Limited and slower image generation',
				'Limited deep research',
				'Limited memory and context'
			]
		},
		{
			name: 'Go',
			tagline: 'Keep chatting with expanded access',
			price: '$8',
			period: '/ month',
			cta: 'Get Go',
			featured: false,
			features: [
				'Everything in Free and:',
				'More access to our flagship model GPT-5.2',
				'More messages',
				'More uploads',
				'More image creation',
				'Longer memory'
			],
			note: 'This plan may include ads. Learn more'
		},
		{
			name: 'Plus',
			tagline: 'Do more with advanced intelligence',
			price: '$20',
			period: '/ month',
			cta: 'Get Plus',
			featured: true,
			note: '',
			features: [
				'Everything in Go and:',
				'Advanced reasoning models',
				'Expanded messages and uploads',
				'Expanded and faster image creation',
				'Expanded deep research and agent mode',
				'Expanded memory and context',
				'Projects, tasks, and custom GPTs',
				'Codex agent and Sora video generation',
				'Early access to new features'
			]
		},
		{
			name: 'Pro',
			tagline: 'Full access to the best of ChatGPT',
			price: '$200',
			period: '/ month',
			cta: 'Get Pro',
			featured: false,
			note: '',
			features: [
				'Everything in Plus and:',
				'Pro reasoning with GPT-5.2 Pro',
				'Unlimited messages and uploads',
				'Unlimited and faster image creation',
				'Maximum deep research and agent mode',
				'Maximum memory and context',
				'Expanded projects, tasks, and custom GPTs',
				'Expanded access to Sora video generation',
				'Expanded, priority-speed Codex agent',
				'Research preview of new features'
			]
		}
	];

	const teamPlans = [
		{
			name: 'Business',
			tagline: 'A secure, collaborative workspace for startups and growing businesses',
			price: '$25 / user / month billed annually',
			cta: 'Try for free',
			features: [
				'Everything in Plus and:',
				'Unlimited GPT-5.2 messages, with generous access to GPT-5.2 Thinking, and access to GPT-5.2 Pro - plus the flexibility to add credits as needed',
				'60+ apps that bring your tools and data into ChatGPT - like Slack, Google Drive, SharePoint, GitHub, Atlassian, and more',
				'A secure, dedicated workspace with essential admin controls, SAML SSO, and MFA',
				'Support for compliance with GDPR, CCPA, and other privacy laws. Aligned with CSA STAR and SOC 2 Type 2',
				'Business features like apps, data analysis, record mode, canvas, shared projects, and custom workspace GPTs',
				'Encryption at rest and in transit, and no training on your business data by default. Learn more',
				'Includes access to Codex and ChatGPT agent for reasoning and taking action across your documents, tools, and codebases'
			]
		},
		{
			name: 'Enterprise',
			tagline: '',
			price: '',
			cta: 'Contact sales',
			features: []
		}
	];

	const tokenUsage = [
		'Tokens are used for messages, tool calls, uploads, and image generation.',
		'Each plan includes a monthly token budget that resets every billing cycle.',
		'Business and Enterprise can add flexible credits for extra usage.',
		'Track remaining tokens and add credits from billing.'
	];

	const comparisonColumns = ['Free', 'Go', 'Plus', 'Pro', 'Business', 'Enterprise'];

	const comparisonGroups = [
		{
			title: 'Essentials',
			rows: [
				{
					feature: 'Messages and interactions',
					values: ['Limited', 'Expanded', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'Chat history',
					values: ['Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'Access on web, iOS, Android',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				}
			]
		},
		{
			title: 'Models',
			rows: [
				{
					feature: 'GPT-5.2 Instant',
					values: ['Yes', 'Expanded', 'Expanded', 'Unlimited*', 'Unlimited*', 'Unlimited*']
				},
				{
					feature: 'GPT-5.2 Thinking',
					values: ['No', 'No', 'Expanded', 'Unlimited*', 'Flexible**', 'Flexible**']
				},
				{
					feature: 'GPT-5.2 Pro',
					values: ['No', 'No', 'No', 'Yes', 'Flexible**', 'Flexible**']
				},
				{
					feature: 'Legacy models',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Response times',
					values: [
						'Limited on bandwidth & availability',
						'Limited on bandwidth & availability',
						'Fast',
						'Fast',
						'Fast',
						'Fastest'
					]
				},
				{
					feature: 'Context window',
					values: ['16K', '32K', '32K', '128K', '32K', '128K']
				},
				{
					feature: 'Regular quality & speed updates as models improve',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				}
			]
		},
		{
			title: 'Features',
			rows: [
				{
					feature: 'Voice',
					values: ['Yes', 'Expanded', 'Expanded', 'Unlimited*', 'Expanded', 'Flexible**']
				},
				{
					feature: 'Voice with video',
					values: ['No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Memory',
					values: ['Limited', 'Yes', 'Expanded', 'Expanded', 'Expanded', 'Expanded']
				},
				{
					feature: 'Memory with past chats',
					values: ['Limited', 'Yes', 'Expanded', 'Expanded', 'Coming soon', 'Coming soon']
				},
				{
					feature: 'Search',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Canvas',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Code edits on macOS',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Projects',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Shared projects',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Tasks',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Data analysis',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Vision',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps connecting to internal tools',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Interactive apps',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'App directory',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Company knowledge',
					values: ['No', 'No', 'No', 'No', 'Yes', 'Yes']
				},
				{
					feature: 'Developer mode (beta)',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'ChatGPT record mode',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'File uploads',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Discover & use GPTs',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Create & share GPTs',
					values: ['No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Share GPTs with your workspace',
					values: ['No', 'No', 'No', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Opportunities to test new features',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Image generation',
					values: ['Limited', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Interactive tables and charts',
					values: ['No', 'No', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Sora 1',
					values: ['No', 'No', 'Limited', 'Expanded', 'Limited', 'No']
				},
				{
					feature: 'Sora 2',
					values: ['Yes', 'Yes', 'Yes', 'Expanded', 'Yes', 'Yes']
				},
				{
					feature: 'Codex agent',
					values: ['No', 'No', 'Yes', 'Expanded', 'Yes', 'Yes']
				},
				{
					feature: 'Deep research',
					values: ['Limited', 'Limited', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Apps for deep research',
					values: ['Limited', 'Limited', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'Study mode',
					values: ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes']
				},
				{
					feature: 'ChatGPT Pulse',
					values: ['No', 'No', 'No', 'Yes', 'No', 'No']
				}
			]
		}
	];
</script>

<div class="fixed inset-0 z-[999] bg-white text-[#1d1424]">
	<div class="h-full w-full overflow-y-auto">
		<div class="mx-auto w-full max-w-8xl px-4 py-8 sm:px-6 lg:px-8">
			<div
				class="rounded-2xl bg-white p-6 shadow-[0_28px_70px_rgba(22,10,30,0.28)] sm:rounded-[28px] sm:p-10"
			>
				<div class="flex flex-col gap-6">
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-3">
							<img
								src="/static/logo.png"
								alt="Synapse logo"
								class="h-10 w-10 rounded-full border border-[rgba(39,20,46,0.14)] object-contain"
							/>
							<span class="text-sm font-semibold tracking-[0.12em] text-[rgba(146,39,143,1)]">
								Synapse
							</span>
						</div>
						<button
							class="rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-xs font-semibold text-white whitespace-nowrap"
							type="button"
							on:click={async () => {
								localStorage.removeItem('token');
								location.href = '/auth';
							}}
						>
							{$i18n.t('Sign Out')}
						</button>
					</div>
					<header class="mx-auto max-w-2xl text-center">
						<h1 class="font-serif text-3xl text-[rgba(146,39,143,1)] font-semibold tracking-[0.02em] sm:text-4xl">
							Pricing
						</h1>
						<p class="mt-2 text-sm text-[#5a4b64] sm:text-base">
							See pricing for our individual, business, and enterprise plans.
						</p>
					</header>
				</div>

				<section class="mt-8 grid gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
					{#each personalPlans as plan}
						<article
							class={`flex h-full flex-col gap-4 rounded-2xl border p-4 sm:p-5 ${
								plan.featured
									? 'border-[rgba(146,39,143,1)]'
									: 'border-[rgba(39,20,46,0.14)]'
							}`}
						>
							<div class="flex flex-col gap-2">
								<div class="text-lg font-semibold">{plan.name}</div>
								<div class="text-sm text-[#5a4b64]">{plan.tagline}</div>
								<div class="flex flex-wrap items-baseline gap-2 font-semibold">
									<span class="text-2xl">{plan.price}</span>
									{#if plan.period}
										<span class="text-sm text-[#5a4b64]">{plan.period}</span>
									{/if}
								</div>
								<button
									class="mt-2 w-fit rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(146,39,143,0.3)]"
									type="button"
								>
									{plan.cta}
								</button>
							</div>
							<ul class="space-y-2 text-sm text-[#5a4b64]">
								{#each plan.features as feature}
									<li class="flex gap-2">
										<span class="mt-[2px] text-[rgba(146,39,143,1)]">&#10004;</span>
										<span>{feature}</span>
									</li>
								{/each}
							</ul>
							{#if plan.note}
								<p class="text-xs text-[#5a4b64]">{plan.note}</p>
							{/if}
						</article>
					{/each}
				</section>

				<div class="mt-4 text-sm text-[#5a4b64]">
					Have an existing plan?
					<span class="font-semibold text-[rgba(146,39,143,1)]">See billing help</span>
				</div>

				<section class="mt-6 grid gap-3 sm:gap-4 md:grid-cols-2">
					{#each teamPlans as plan}
						<article
							class="flex h-full flex-col gap-4 rounded-2xl border border-[rgba(39,20,46,0.14)] p-4 sm:p-5"
						>
							<div class="flex flex-col gap-2">
								<div class="text-lg font-semibold">{plan.name}</div>
								{#if plan.tagline}
									<div class="text-sm text-[#5a4b64]">{plan.tagline}</div>
								{/if}
								{#if plan.price}
									<div class="text-lg font-semibold">{plan.price}</div>
								{/if}
								<button
									class="mt-2 w-fit rounded-full bg-[rgba(146,39,143,1)] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(146,39,143,0.3)]"
									type="button"
								>
									{plan.cta}
								</button>
							</div>
							{#if plan.features.length}
								<ul class="space-y-2 text-sm text-[#5a4b64]">
									{#each plan.features as feature}
										<li class="flex gap-2">
											<span class="mt-[2px] text-[rgba(146,39,143,1)]">&#10004;</span>
											<span>{feature}</span>
										</li>
									{/each}
								</ul>
							{/if}
						</article>
					{/each}
				</section>

				<section class="mt-8 rounded-2xl border border-[rgba(146,39,143,0.12)] bg-[rgba(146,39,143,0.06)] p-4 sm:p-5">
					<h2 class="text-lg font-semibold">Token usage when you purchase a plan</h2>
					<ul class="mt-3 space-y-2 text-sm text-[#5a4b64]">
						{#each tokenUsage as item}
							<li class="flex gap-2">
								<span class="mt-[2px] text-[rgba(146,39,143,1)]">&#10004;</span>
								<span>{item}</span>
							</li>
						{/each}
					</ul>
				</section>

				<section class="mt-8">
					<h2 class="text-lg font-semibold">Compare features across plans</h2>
					<div class="mt-4 overflow-x-auto rounded-2xl border border-[rgba(39,20,46,0.14)]">
						<table class="min-w-[760px] w-full border-collapse text-sm">
							<thead class="bg-[rgba(146,39,143,0.08)] text-left">
								<tr>
									<th class="px-3 py-3 font-semibold sm:px-4">Feature</th>
									{#each comparisonColumns as column}
										<th class="px-3 py-3 font-semibold sm:px-4">{column}</th>
									{/each}
								</tr>
							</thead>
							{#each comparisonGroups as group}
								<tbody>
									<tr class="bg-[rgba(16,10,24,0.04)]">
										<th
											colspan={comparisonColumns.length + 1}
											class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] sm:px-4"
										>
											{group.title}
										</th>
									</tr>
									{#each group.rows as row}
										<tr class="border-t border-[rgba(39,20,46,0.14)]">
											<th class="px-3 py-3 text-left font-semibold text-[#1d1424] sm:px-4">
												{row.feature}
											</th>
											{#each row.values as value}
												<td class="px-3 py-3 align-top text-[#5a4b64] sm:px-4">{value}</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							{/each}
						</table>
					</div>
				</section>

				<div class="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
					<button
						class="w-fit rounded-full border border-[rgba(39,20,46,0.2)] px-5 py-2 text-sm font-semibold text-[#1d1424]"
						type="button"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{$i18n.t('Check Again')}
					</button>
				</div>

				<footer class="mt-10 border-t border-[rgba(39,20,46,0.14)] pt-6 text-xs text-[#5a4b64]">
					<div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
						<div class="flex items-start gap-3 sm:items-center">
							<img
								src="/static/logo.png"
								alt="Synapse logo"
								class="h-9 w-9 rounded-full border border-[rgba(39,20,46,0.14)] object-contain"
							/>
							<div>
								<div class="text-sm font-semibold text-[#1d1424]">Synapse</div>
								<div class="text-xs text-[#5a4b64]">Intelligence for teams and creators.</div>
							</div>
						</div>
						<div class="text-left">
							<div class="text-sm font-semibold text-[#1d1424]">Contact</div>
							<div class="mt-2">support@synapse.ai</div>
							
						</div>
						<div class="text-left lg:text-right">
							<div class="text-sm font-semibold text-[#1d1424]">Legal</div>
							<div class="mt-2">Privacy | Terms | Security</div>
							<div class="mt-1">Copyright {currentYear} Synapse. All rights reserved.</div>
						</div>
					</div>
				</footer>
			</div>
		</div>
	</div>
</div>



