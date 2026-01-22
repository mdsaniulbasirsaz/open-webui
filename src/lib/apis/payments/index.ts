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
