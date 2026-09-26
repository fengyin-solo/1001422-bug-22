<template>
  <section class="page" data-module="accept">
    <header class="page-head">
      <div>
        <h2>竣工验收管理</h2>
        <p class="page-desc">维护验收单，围绕验收单号、关联施工、验收项目、验收标准做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记验收单</button>
        <button class="btn" type="button" @click="exportRows">导出竣工验收清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>验收单号</span>
        <input v-model="keywordDraft" placeholder="按验收单号检索" />
      </label>
      <label class="filter-item">
        <span>验收状态</span>
        <select v-model="statusDraft">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无竣工验收数据，可先登记验收单</td>
        </tr>
      </tbody>
    </table>

    <div class="pager">
      <button class="btn" type="button" :disabled="pageState.page <= 1" @click="gotoPage(pageState.page - 1)">上一页</button>
      <span class="pager-info">第 {{ pageState.page }} / {{ pages }} 页 · 本页 {{ rows.length }} 条</span>
      <button class="btn" type="button" :disabled="pageState.page >= pages" @click="gotoPage(pageState.page + 1)">下一页</button>
      <label class="pager-item">
        <span>每页</span>
        <select :value="pageState.size" @change="changeSize(Number(($event.target as HTMLSelectElement).value))">
          <option v-for="option in sizeOptions" :key="option" :value="option">{{ option }}</option>
        </select>
        <span>条</span>
      </label>
      <form class="pager-item" @submit.prevent="jumpToPage">
        <span>跳至</span>
        <input v-model="jumpDraft" class="pager-jump" inputmode="numeric" placeholder="页码" />
        <span>页</span>
        <button class="btn" type="submit">跳转</button>
      </form>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条竣工验收记录 · 每页 {{ pageState.size }} 条 · 共 {{ pages }} 页</span>
      <span v-if="notice" class="notice-text">{{ notice }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="detail" class="dialog-mask" @click.self="closeDetail">
      <div class="dialog" role="dialog" aria-label="验收单详情">
        <header class="dialog-head">
          <h3>验收单详情</h3>
          <button class="link" type="button" @click="closeDetail">关闭</button>
        </header>
        <dl class="dialog-body">
          <template v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detail[column] ?? '—' }}</dd>
          </template>
        </dl>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'
import { useAcceptPageStore } from '@/stores/acceptPage'

type Row = Record<string, string | number | null>

type ListPayload = {
  items: Row[]
  total: number
  page: number
  size: number
  pages: number | null
  notice: string | null
  stats: Record<string, number> | null
}

const ENDPOINT = '/api/accept'
const columns = ["验收单号", "关联施工", "验收项目", "验收标准", "验收结论", "验收人员", "验收日期", "验收状态"]
const actions = ["开始验收", "确认通过", "下发返工"]
const statuses = ["待验收", "验收中", "已通过", "需返工", "已作废"]
const sizeOptions = [10, 20, 50]

const pageState = useAcceptPageStore()

const rows = ref<Row[]>([])
const total = ref(0)
const pages = ref(1)
const notice = ref('')
const errorMessage = ref('')
const keywordDraft = ref(pageState.keyword)
const statusDraft = ref(pageState.status)
const jumpDraft = ref('')
const detail = ref<Row | null>(null)
const statusCounts = ref<Record<string, number>>({})

const stats = computed(() => {
  const counts = statusCounts.value
  return [
    { label: '待验收单据', value: counts['待验收'] ?? 0 },
    { label: '本月通过数', value: counts['已通过'] ?? 0 },
    { label: '需返工项数', value: counts['需返工'] ?? 0 },
    { label: '已作废', value: counts['已作废'] ?? 0 },
  ]
})

function applyFilters() {
  pageState.applyFilters(keywordDraft.value.trim(), statusDraft.value)
  void reload()
}

function resetFilters() {
  keywordDraft.value = ''
  statusDraft.value = ''
  pageState.resetFilters()
  void reload()
}

function gotoPage(page: number) {
  pageState.gotoPage(page)
  void reload()
}

function jumpToPage() {
  const raw = jumpDraft.value.trim()
  jumpDraft.value = ''
  const target = Number(raw)
  if (!raw || !Number.isInteger(target)) {
    notice.value = '跳转页码不合法：请输入整数页码'
    return
  }
  gotoPage(target)
}

function changeSize(size: number) {
  pageState.changeSize(size)
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '验收单登记入口尚未接入审批流'
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) {
      throw new Error('验收单详情读取失败')
    }
    detail.value = (await response.json()) as Row
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '验收单详情读取失败'
  }
}

function closeDetail() {
  // 只关详情，不动列表分页：回来后还是原来那一页。
  detail.value = null
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('竣工验收动作未生效，请稍后重试')
    }
    const result = (await response.json()) as { ok: boolean; message: string }
    if (!result.ok) {
      throw new Error(result.message || '竣工验收动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '竣工验收操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (pageState.keyword) {
    query.set('keyword', pageState.keyword)
  }
  if (pageState.status) {
    query.set('status', pageState.status)
  }
  query.set('page', String(pageState.page))
  query.set('size', String(pageState.size))
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error('验收单列表读取失败')
    }
    const payload = (await response.json()) as ListPayload
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    pages.value = payload.pages ?? 1
    statusCounts.value = payload.stats ?? {}
    notice.value = payload.notice ?? ''
    if (payload.page !== pageState.page) {
      // 页码越界被后端校正时，以实际生效的页码为准。
      pageState.gotoPage(payload.page)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '竣工验收列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.pager {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
  font-size: 13px;
}
.pager-info {
  color: var(--muted);
}
.pager-item {
  display: flex;
  gap: 6px;
  align-items: center;
  color: var(--muted);
}
.pager-jump {
  width: 64px;
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.notice-text {
  color: #b45309;
}
.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.dialog {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  width: 420px;
  max-height: 80vh;
  overflow: auto;
}
.dialog-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dialog-head h3 {
  margin: 0;
  font-size: 15px;
}
.dialog-body {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 8px 12px;
  margin: 12px 0 0;
  font-size: 13px;
}
.dialog-body dt {
  color: var(--muted);
}
.dialog-body dd {
  margin: 0;
}
</style>
