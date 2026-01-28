import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TokenBudget = {
	id: string;
	user_id: string;
	window_type: string;
	timezone?: string | null;
	limit_tokens: number;
	enabled: boolean;
	created_by: string;
	created_at: number;
	updated_at: number;
};

export type TokenBudgetStatus = {
	user_id: string;
	enabled: boolean;
	window_type: string;
	timezone?: string | null;
	window_start: number;
	reset_at: number;
	limit_tokens: number;
	used_tokens: number;
	reserved_tokens: number;
	remaining_tokens: number;
};

export type UpsertTokenBudgetForm = {
	limit_tokens: number;
	enabled?: boolean;
	timezone?: string | null;
};

export const upsertUserTokenBudget = async (
	token: string,
	user_id: string,
	body: UpsertTokenBudgetForm
): Promise<TokenBudget> => {
	let error: string | null = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/admin/token-budgets/users/${encodeURIComponent(user_id)}`,
		{
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
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

export const getUserTokenBudgetStatus = async (
	token: string,
	user_id: string
): Promise<TokenBudgetStatus> => {
	let error: string | null = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/admin/token-budgets/users/${encodeURIComponent(user_id)}/status`,
		{
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
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
