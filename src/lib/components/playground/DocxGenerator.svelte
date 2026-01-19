<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import { config, models, settings } from '$lib/stores';
	import { generateDocxReport, renderDocxFromMarkdown } from '$lib/apis/documents';

	const i18n = getContext('i18n');

	let prompt = '';
	let draftMarkdown = '';
	let previewHtml = '';
	let selectedModelId = '';
	let fileName = 'report.docx';
	let docxBase64 = '';
	let originalMarkdown = '';
	let ready = false;
	let generating = false;
	let downloading = false;

	const docxMime =
		'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

	const buildPreviewHtml = (value: string) => {
		if (!ready) return '';
		return DOMPurify.sanitize(marked.parse(value || ''));
	};

	const base64ToBlob = (base64: string) => {
		const byteCharacters = atob(base64);
		const byteNumbers = new Array(byteCharacters.length);
		for (let i = 0; i < byteCharacters.length; i += 1) {
			byteNumbers[i] = byteCharacters.charCodeAt(i);
		}
		return new Blob([new Uint8Array(byteNumbers)], { type: docxMime });
	};

	const generateReport = async () => {
		const trimmedPrompt = prompt.trim();
		if (!selectedModelId) {
			toast.error($i18n.t('Select a model first.'));
			return;
		}
		if (!trimmedPrompt) {
			toast.error($i18n.t('Enter a prompt to generate a report.'));
			return;
		}

		generating = true;
		try {
			const res = await generateDocxReport(localStorage.token, {
				prompt: trimmedPrompt,
				model: selectedModelId
			});

			draftMarkdown = res?.content ?? '';
			originalMarkdown = draftMarkdown;
			docxBase64 = res?.docx ?? '';
			fileName = res?.file_name ?? 'report.docx';
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			generating = false;
		}
	};

	const downloadDocx = async () => {
		const trimmedContent = draftMarkdown.trim();
		if (!trimmedContent) {
			toast.error($i18n.t('Generate or paste content before downloading.'));
			return;
		}

		downloading = true;
		try {
			if (trimmedContent === originalMarkdown && docxBase64) {
				saveAs(base64ToBlob(docxBase64), fileName);
				return;
			}

			const blob = await renderDocxFromMarkdown(localStorage.token, {
				content: trimmedContent,
				html: previewHtml,
				file_name: fileName
			});

			if (blob) {
				saveAs(blob, fileName);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			downloading = false;
		}
	};

	onMount(() => {
		const options = { throwOnError: false };
		marked.use(markedKatexExtension(options));
		marked.use(markedExtension(options));

		if ($settings?.models) {
			selectedModelId = $settings.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}
		ready = true;
	});

	$: previewHtml = buildPreviewHtml(draftMarkdown);
</script>

<div class="flex flex-col h-full w-full bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-950 dark:via-gray-950 dark:to-gray-900">
	<div class="px-4 pt-4 pb-5 border-b border-gray-100/60 dark:border-gray-850/50">
		<div class="flex flex-col gap-4">
			<div class="flex flex-col gap-1">
				<div class="text-lg font-semibold tracking-tight">Build Docx File</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					Generate DOCX with a live Markdown editor and scrollable preview.
				</div>
			</div>

			<div class="flex flex-col gap-3">
				<div class="text-[11px] uppercase tracking-[0.2em] text-gray-500">Prompt</div>
				<textarea
					class="w-full p-3 bg-white/80 dark:bg-gray-950/70 border border-gray-200/70 dark:border-gray-800/70 outline-hidden resize-none rounded-xl text-sm shadow-sm focus:border-gray-300 dark:focus:border-gray-700"
					rows="3"
					bind:value={prompt}
					placeholder="Generate a DOCX report about ML pipelines"
				/>

				<div class="flex flex-col gap-2">
					<div class="text-[11px] uppercase tracking-[0.2em] text-gray-500">Model + Actions</div>
					<div class="flex items-center gap-2 flex-nowrap overflow-x-auto scrollbar-hidden">
						<div class="w-44 shrink-0">
							<Selector
								placeholder={$i18n.t('Select a model')}
								items={$models.map((model) => ({
									value: model.id,
									label: model.name,
									model: model
								}))}
								bind:value={selectedModelId}
							/>
						</div>
						<button
							class="shrink-0 px-3.5 py-1.5 text-sm font-medium rounded-full transition {generating
								? 'bg-gray-300 text-black'
								: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100'}"
							on:click={generateReport}
							disabled={generating}
						>
							{generating ? $i18n.t('Generating...') : $i18n.t('Generate')}
						</button>
						<button
							class="shrink-0 px-3.5 py-1.5 text-sm font-medium rounded-full border border-gray-200 dark:border-gray-800 transition {downloading
								? 'text-gray-400'
								: 'hover:bg-gray-50 dark:hover:bg-gray-900'}"
							on:click={downloadDocx}
							disabled={downloading || !draftMarkdown.trim()}
						>
							{downloading ? $i18n.t('Preparing...') : $i18n.t('Download DOCX')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div class="flex-1 px-4 py-4 overflow-hidden">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-full min-h-0">
			<div class="flex flex-col h-full min-h-0 gap-2">
				<div class="text-[11px] uppercase tracking-[0.2em] text-gray-500">Markdown</div>
				<textarea
					class="flex-1 min-h-0 w-full p-3 bg-white/90 dark:bg-gray-950/70 border border-gray-200/70 dark:border-gray-800/70 outline-hidden resize-none rounded-xl text-sm shadow-sm"
					bind:value={draftMarkdown}
					placeholder="Markdown output appears here."
				/>
			</div>

			<div class="flex flex-col h-full min-h-0 gap-2">
				<div class="text-[11px] uppercase tracking-[0.2em] text-gray-500">Preview</div>
				<div
					class="flex-1 min-h-0 w-full p-4 border border-gray-200/70 dark:border-gray-800/70 rounded-xl overflow-auto text-sm markdown-prose bg-white/90 dark:bg-gray-950/70 shadow-sm"
				>
					{@html previewHtml}
				</div>
			</div>
		</div>
	</div>
</div>
