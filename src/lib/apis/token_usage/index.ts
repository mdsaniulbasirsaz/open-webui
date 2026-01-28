import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TokenUsageSummary = {
	window_start: number;
	window_end: number;
	limit_tokens: number;
	used_tokens: number;
	reserved_tokens: number;
	remaining_tokens: number;
	used_percent: number;
	timezone?: string | null;
};

export type TokenUsageSeriesPoint = {
	date: string;
	tokens: number;
	top_model?: string | null;
};

export type TokenUsageModelBreakdownRow = {
	model: string;
	tokens: number;
	share: number;
};

export type TokenUsageActivityRow = {
	id: string;
	timestamp: number;
	model: string;
	type: string;
	input_tokens: number;
	output_tokens: number;
	total_tokens: number;
	conversation_id?: string | null;
};

export type TokenUsageActivityDetail = TokenUsageActivityRow & {
	metadata?: Record<string, unknown> | null;
};

export type TokenUsageQueryParams = {
	start?: string;
	end?: string;
	timezone?: string;
	model?: string;
	type?: string;
	page?: number;
	limit?: number;
};

const buildSearchParams = (params?: TokenUsageQueryParams) => {
	const searchParams = new URLSearchParams();
	if (!params) return searchParams;
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	return searchParams;
};

const buildAuthHeaders = (token?: string) => {
	return {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {})
	};
};

export const getTokenUsageSummary = async (
	token: string,
	params?: TokenUsageQueryParams
): Promise<TokenUsageSummary> => {
	let error: string | null = null;
	const searchParams = buildSearchParams(params);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/token-usage/summary?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: buildAuthHeaders(token),
			credentials: 'include'
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err?.message ?? 'Request failed';
			return null;
		});

	if (error) throw error;
	return res?.data ?? res;
};

export const getTokenUsageSeries = async (
	token: string,
	params?: TokenUsageQueryParams
): Promise<TokenUsageSeriesPoint[]> => {
	let error: string | null = null;
	const searchParams = buildSearchParams(params);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/token-usage/series?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: buildAuthHeaders(token),
			credentials: 'include'
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err?.message ?? 'Request failed';
			return null;
		});

	if (error) throw error;
	return res?.data ?? res ?? [];
};

export const getTokenUsageByModel = async (
	token: string,
	params?: TokenUsageQueryParams
): Promise<TokenUsageModelBreakdownRow[]> => {
	let error: string | null = null;
	const searchParams = buildSearchParams(params);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/token-usage/models?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: buildAuthHeaders(token),
			credentials: 'include'
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err?.message ?? 'Request failed';
			return null;
		});

	if (error) throw error;
	return res?.data ?? res ?? [];
};

export const getTokenUsageActivity = async (
	token: string,
	params?: TokenUsageQueryParams
): Promise<{ data: TokenUsageActivityRow[]; page: number; total: number }> => {
	let error: string | null = null;
	const searchParams = buildSearchParams(params);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/token-usage/activity?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: buildAuthHeaders(token),
			credentials: 'include'
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err?.message ?? 'Request failed';
			return null;
		});

	if (error) throw error;
	return res;
};

export const getTokenUsageActivityDetail = async (
	token: string,
	activityId: string
): Promise<TokenUsageActivityDetail> => {
	let error: string | null = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/token-usage/activity/${encodeURIComponent(activityId)}`,
		{
			method: 'GET',
			headers: buildAuthHeaders(token),
			credentials: 'include'
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err?.message ?? 'Request failed';
			return null;
		});

	if (error) throw error;
	return res;
};
