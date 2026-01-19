import { WEBUI_API_BASE_URL } from '$lib/constants';

type DocxGenerateRequest = {
	prompt: string;
	model: string;
	temperature?: number;
	max_tokens?: number;
};

type DocxGenerateResponse = {
	content: string;
	html: string;
	docx: string;
	file_name: string;
};

type DocxRenderRequest = {
	content: string;
	html?: string;
	file_name?: string;
};

export const generateDocxReport = async (
	token: string,
	body: DocxGenerateRequest
): Promise<DocxGenerateResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/docx/generate`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const renderDocxFromMarkdown = async (
	token: string,
	body: DocxRenderRequest
): Promise<Blob> => {
	let error = null;

	const blob = await fetch(`${WEBUI_API_BASE_URL}/documents/docx`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.blob();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return blob;
};
