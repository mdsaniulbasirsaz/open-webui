<script>
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditUserModal from '$lib/components/admin/Users/UserList/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/Users/UserList/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/Users/UserList/AddUserModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import RoleUpdateConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Badge from '$lib/components/common/Badge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import About from '$lib/components/chat/Settings/About.svelte';
	import Banner from '$lib/components/common/Banner.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';

	const i18n = getContext('i18n');

	let page = 1;

	let users = null;
	let total = null;

	let query = '';
	let orderBy = 'created_at'; // default sort key
	let direction = 'asc'; // default sort order

	let selectedUser = null;

	let showDeleteConfirmDialog = false;
	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		// if the user is deleted and the current page has only one user, go back to the previous page
		if (users.length === 1 && page > 1) {
			page -= 1;
		}

		if (res) {
			getUserList();
		}
	};

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const getUserList = async () => {
		try {
			const res = await getUsers(localStorage.token, query, orderBy, direction, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				users = res.users;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	$: if (query !== null && page !== null && orderBy !== null && direction !== null) {
		getUserList();
	}
	const ACCENT_COLORS = [
    '#6366f1',   // indigo
    '#8b5cf6',   // violet
    '#ec4899',   // pink
    '#f43f5e',   // rose
    '#f97316',   // orange
    '#eab308',   // yellow
    '#10b981',   // emerald
    '#06b6d4',   // cyan
    '#3b82f6',   // blue
    '#a855f7',   // purple
    '#ef4444',   // red
    '#14b8a6'    // teal
  ];

  function getRowAccentColor(index) {
    return ACCENT_COLORS[index % ACCENT_COLORS.length];
  }
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteUserHandler(selectedUser.id);
	}}
/>

<AddUserModal
	bind:show={showAddUserModal}
	on:save={async () => {
		getUserList();
	}}
/>

<EditUserModal
	bind:show={showEditUserModal}
	{selectedUser}
	sessionUser={$user}
	on:save={async () => {
		getUserList();
	}}
/>

{#if selectedUser}
	<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />
{/if}

{#if ($config?.license_metadata?.seats ?? null) !== null && total && total > $config?.license_metadata?.seats}
	<div class=" mt-1 mb-2 text-xs text-red-500">
		<Banner
			className="mx-0"
			banner={{
				type: 'error',
				title: 'License Error',
				content:
					'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
			}}
		/>
	</div>
{/if}

{#if users === null || total === null}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else}
	<div
		class="pt-0.5 pb-1 gap-1 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900"
	>
		<div class="flex md:self-center text-md font-medium px-0.5 gap-2">
			<div class="flex-shrink-0">
				{$i18n.t('Users')}
			</div>

			<div>
				{#if ($config?.license_metadata?.seats ?? null) !== null}
					{#if total > $config?.license_metadata?.seats}
						<span class="text-lg font-medium text-red-500"
							>{total} of {$config?.license_metadata?.seats}
							<span class="text-sm font-normal">{$i18n.t('available users')}</span></span
						>
					{:else}
						<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
							>{total} of {$config?.license_metadata?.seats}
							<span class="text-sm font-normal">{$i18n.t('available users')}</span></span
						>
					{/if}
				{:else}
					<span class="text-lg font-medium text-gray-500 dark:text-gray-300 rounded-full bg-gray-200 px-2 py-1 dark:bg-gray-700">{total}</span>
				{/if}
			</div>
		</div>

		<div class="flex gap-1">
			<div class=" flex w-full space-x-2">
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3 bg-green-300/30 rounded-full p-1">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 text-center text-gray-900 rounded bg-green-500/10"
						bind:value={query}
						placeholder={$i18n.t('Search')}
					/>
				</div>

				<div>
					<Tooltip content={$i18n.t('Add User')}>
						<button
							class=" p-2 px-4 rounded text-white bg-green-600 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
							on:click={() => {
								showAddUserModal = !showAddUserModal;
							}}
						>
							<span class=""> + Add User</span>
						</button> 
					</Tooltip>
				</div>
			</div>
		</div>
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700/70 text-sm">
			<!-- Header -->
			<thead class="bg-yellow-300 dark:bg-gray-800/60 backdrop-blur-sm sticky top-0 z-10">
			<tr>
				<th scope="col" class="px-5 py-4 text-left text-xs font-bolder uppercase tracking-wider text-gray-700 dark:text-gray-300">
				 Role
				</th>
				<th scope="col" class="px-5 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
				Name
				</th>
				<th scope="col" class="px-5 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
				Email
				</th>
				<th scope="col" class="px-5 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
				Last Active
				</th>
				<th scope="col" class="px-5 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
				Created
				</th>
				<th scope="col" class="relative px-5 py-4">
				<span class="sr-only">Actions</span>
				</th>
			</tr>
			</thead>

			<!-- Body -->
			<tbody class="divide-y divide-gray-100 dark:divide-gray-800/50 bg-white dark:bg-gray-900">
			{#each users as user, index (user.id)}
				<tr 
				class="group transition-colors duration-150 hover:bg-gray-50/70 dark:hover:bg-gray-800/40"
				style="border-left: 4px solid {getRowAccentColor(index)};"
				>
				<td class="whitespace-nowrap px-5 py-4">
					<button
					on:click={() => {
						selectedUser = user;
						showEditUserModal = true;
					}}
					class="inline-flex focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500/40 rounded-full transition"
					>
					<Badge
						type={user.role === 'admin' ? 'info' : user.role === 'user' ? 'success' : 'muted'}
						content={$i18n.t(user.role)}
						class="text-xs font-medium px-4 py-2"
					/>
					</button>
				</td>

				<td class="whitespace-nowrap px-5 py-4">
					<div class="flex items-center gap-3">
					<ProfilePreview {user} side="right" align="center" sideOffset={8}>
						<div class="relative">
						<img
							class="h-9 w-9 rounded-full object-cover ring-1 ring-gray-200/70 dark:ring-gray-700/60 flex-shrink-0 shadow-sm"
							src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
							alt={user.name || 'User'}
						/>
						{#if user?.last_active_at && Date.now() / 1000 - user.last_active_at < 180}
							<span class="absolute bottom-0 right-0 block h-2.5 w-2.5">
							<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-70"></span>
							<span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500 ring-1 ring-white dark:ring-gray-900"></span>
							</span>
						{/if}
						</div>
					</ProfilePreview>

					<span class="font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]">
						{user.name}
					</span>
					</div>
				</td>

				<td class="whitespace-nowrap px-5 py-4 text-gray-600 dark:text-gray-300">
					{user.email}
				</td>

				<td class="whitespace-nowrap px-5 py-4 text-gray-600 dark:text-gray-300">
					{user.last_active_at ? dayjs(user.last_active_at * 1000).fromNow() : 'Never'}
				</td>

				<td class="whitespace-nowrap px-5 py-4 text-gray-600 dark:text-gray-300">
					{dayjs(user.created_at * 1000).format('LL')}
				</td>

				<td class="whitespace-nowrap px-5 py-4 text-right">
					<div class="flex items-center justify-end gap-1 opacity-70 group-hover:opacity-100 transition-opacity duration-150">
					{#if $config.features.enable_admin_chat_access && user.role !== 'admin'}
						<Tooltip content={$i18n.t('View Chats')}>
						<button
							on:click={() => {
							selectedUser = user;
							showUserChatsModal = true;
							}}
							class="p-1.5 bg-green-500 rounded-md text-white hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 hover:bg-gray-100/80 dark:hover:bg-gray-700/40 transition-colors"
						>
							<ChatBubbles class="w-4 h-4" />
						</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('Edit User')}>
						<button
						on:click={() => {
							selectedUser = user;
							showEditUserModal = true;
						}}
						class="p-1.5 bg-blue-600 rounded-md text-white hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-gray-700/40 transition-colors"
						>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.9" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 1 0 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487m0 0L19.5 7.125" />
						</svg>
						</button>
					</Tooltip>

					{#if user.role !== 'admin'}
						<Tooltip content={$i18n.t('Delete User')}>
						<button
							on:click={() => {
							selectedUser = user;
							showDeleteConfirmDialog = true;
							}}
							class="p-1.5 bg-red-600 rounded-md text-white hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-gray-700/40 transition-colors"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.9" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12.562.165c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
							</svg>
						</button>
						</Tooltip>
					{/if}
					</div>
				</td>
				</tr>
			{/each}
			</tbody>
		</table>
	</div>

	<div class=" text-gray-900 text-xs mt-1.5 text-right">
		🟢 {$i18n.t("Click on the user role button to change a user's role.")}
	</div>

	{#if total > 20}
		<Pagination bind:page count={total} perPage={30} />
	{/if}
{/if}

{#if !$config?.license_metadata}
	{#if total > 50}
		<div class="text-sm">
			<Markdown
				content={`
> [!NOTE]
> # **Hey there! 👋**
>
> It looks like you have over 50 users, that usually falls under organizational usage.
> 
> Open WebUI is completely free to use as-is, with no restrictions or hidden limits, and we'd love to keep it that way. 🌱  
>
> By supporting the project through sponsorship or an enterprise license, you’re not only helping us stay independent, you’re also helping us ship new features faster, improve stability, and grow the project for the long haul. With an *enterprise license*, you also get additional perks like dedicated support, customization options, and more, all at a fraction of what it would cost to build and maintain internally.  
> 
> Your support helps us stay independent and continue building great tools for everyone. 💛
> 
> - 👉 **[Click here to learn more about enterprise licensing](https://docs.openwebui.com/enterprise)**
> - 👉 *[Click here to sponsor the project on GitHub](https://github.com/sponsors/tjbck)*
`}
			/>
		</div>
	{/if}
{/if}
