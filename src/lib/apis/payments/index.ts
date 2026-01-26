import { WEBUI_API_BASE_URL } from '$lib/constants';

type CreateBkashPaymentForm = {
	plan_id?: string;
	amount: number;
	currency?: string;
	payer_reference?: string;
	merchant_invoice_number?: string;
	intent?: string;
	mode?: string;
};

type ExecuteBkashPaymentForm = {
	payment_id: string;
};

export type AdminPaymentTransactionsParams = {
	user_id?: string;
	status?: string;
	payment_id?: string;
	trx_id?: string;
	merchant_invoice_number?: string;
	user_query?: string;
	start_date?: number;
	end_date?: number;
	page?: number;
	page_size?: number;
};

export type UserPaymentTransactionsParams = Omit<AdminPaymentTransactionsParams, 'user_id' | 'user_query'>;

const assertBearerToken = (token?: string | null) => {
	const trimmed = token?.trim();
	if (!trimmed) {
		throw 'Please sign in to continue.';
	}
	return trimmed;
};

const readJsonOrText = async (res: Response) => {
	const text = await res.text();
	if (!text) return null;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
};

const extractErrorMessage = (payload: unknown, status: number) => {
	if (typeof payload === 'string') {
		return payload;
	}
	if (payload && typeof payload === 'object') {
		const payloadRecord = payload as Record<string, unknown>;
		if (typeof payloadRecord.detail === 'string') {
			return payloadRecord.detail;
		}
		if (typeof payloadRecord.message === 'string') {
			return payloadRecord.message;
		}
	}
	return `Request failed with status ${status}.`;
};

const normalizeErrorMessage = (err: unknown) => {
	if (typeof err === 'string') {
		return err;
	}
	if (err && typeof err === 'object') {
		const errRecord = err as Record<string, unknown>;
		if (typeof errRecord.detail === 'string') {
			return errRecord.detail;
		}
		if (typeof errRecord.message === 'string') {
			return errRecord.message;
		}
	}
	return 'Request failed. Please try again.';
};

const fetchJson = async (url: string, options: RequestInit) => {
	try {
		const res = await fetch(url, options);
		const payload = await readJsonOrText(res);
		if (!res.ok) {
			throw new Error(extractErrorMessage(payload, res.status));
		}
		return payload;
	} catch (err) {
		console.error(err);
		throw normalizeErrorMessage(err);
	}
};

const fetchBlob = async (url: string, options: RequestInit) => {
	try {
		const res = await fetch(url, options);
		if (!res.ok) {
			const payload = await readJsonOrText(res);
			throw new Error(extractErrorMessage(payload, res.status));
		}
		return await res.blob();
	} catch (err) {
		console.error(err);
		throw normalizeErrorMessage(err);
	}
};

export const createBkashPayment = async (token: string, body: CreateBkashPaymentForm) =>
	fetchJson(`${WEBUI_API_BASE_URL}/payments/bkash/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		},
		body: JSON.stringify(body)
	});

export const executeBkashPayment = async (token: string, body: ExecuteBkashPaymentForm) =>
	fetchJson(`${WEBUI_API_BASE_URL}/payments/bkash/execute`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		},
		body: JSON.stringify(body)
	});

export const queryBkashPayment = async (token: string, payment_id: string) => {
	const searchParams = new URLSearchParams({ payment_id });
	return fetchJson(`${WEBUI_API_BASE_URL}/payments/bkash/query?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminListPaymentTransactions = async (
	token: string,
	params: AdminPaymentTransactionsParams = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/transactions?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/transactions`;

	return fetchJson(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminPaymentMetrics = async (
	token: string,
	params: AdminPaymentTransactionsParams = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/metrics?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/metrics`;

	return fetchJson(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminPaymentKpis = async (
	token: string | null | undefined,
	params: Pick<AdminPaymentTransactionsParams, 'status' | 'start_date' | 'end_date'> = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/kpis?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/kpis`;

	const headers: Record<string, string> = {
		Accept: 'application/json',
		'Content-Type': 'application/json'
	};
	const trimmed = token?.trim();
	if (trimmed) {
		headers.Authorization = `Bearer ${trimmed}`;
	}

	return fetchJson(url, {
		method: 'GET',
		headers
	});
};

export const adminPaymentUsersSummary = async (
	token: string,
	params: Pick<AdminPaymentTransactionsParams, 'status' | 'start_date' | 'end_date'> & {
		user_ids?: string;
	} = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/users/summary?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/users/summary`;

	return fetchJson(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminExportPaymentTransactions = async (
	token: string,
	params: Omit<AdminPaymentTransactionsParams, 'page' | 'page_size'> = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/transactions/export?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/transactions/export`;

	return fetchBlob(url, {
		method: 'GET',
		headers: {
			Accept: 'text/csv',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminPaymentPlansSummary = async (
	token: string,
	params: Pick<AdminPaymentTransactionsParams, 'start_date' | 'end_date'> = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/admin/payments/plans/summary?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/admin/payments/plans/summary`;

	return fetchJson(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const adminPlanTotalAmount = async (token: string, plan_id: string) => {
	const searchParams = new URLSearchParams({ plan_id });
	return fetchJson(`${WEBUI_API_BASE_URL}/payments/admin/transactions/plans?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};

export const listMyPaymentTransactions = async (
	token: string,
	params: UserPaymentTransactionsParams = {}
) => {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== '') {
			searchParams.set(key, String(value));
		}
	});
	const queryString = searchParams.toString();
	const url = queryString
		? `${WEBUI_API_BASE_URL}/payments/transactions?${queryString}`
		: `${WEBUI_API_BASE_URL}/payments/transactions`;

	return fetchJson(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${assertBearerToken(token)}`
		}
	});
};
