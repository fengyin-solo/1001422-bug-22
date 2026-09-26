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
        <input v-model="filters.keyword" placeholder="按验收单号检索" />
      </label>
      <label class="filter-item">
        <span>验收状态</span>
        <select v-model="filters.status">
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
            <button class="link" type="button" @click="openDetail(row)">查看</button>
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

    <div class="pager-bar">
      <button class="btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
      <span class="pager-info">第 {{ page }} / {{ pageCount }} 页</span>
      <button class="btn" type="button" :disabled="page >= pageCount" @click="goPage(page + 1)">下一页</button>
      <label class="pager-item">
        每页
        <select v-model.number="size" @change="changeSize">
          <option v-for="option in sizeOptions" :key="option" :value="option">{{ option }}</option>
        </select>
        条
      </label>
      <span class="pager-item">
        跳至
        <input v-model="jumpTarget" class="pager-input" type="number" @keyup.enter="jumpToPage" />
        页
        <button class="btn" type="button" @click="jumpToPage">跳转</button>
      </span>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条竣工验收记录 · 第 {{ page }} / {{ pageCount }} 页 · 本页 {{ rows.length }} 条</span>
      <span v-if="noticeMessage" class="notice-text">{{ noticeMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="detail" class="detail-mask" @click.self="closeDetail">
      <aside class="detail-panel">
        <header class="detail-head">
          <h3>验收单明细</h3>
          <button class="btn ghost" type="button" @click="closeDetail">关闭</button>
        </header>
        <dl class="detail-grid">
          <template v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detail[column] ?? '—' }}</dd>
          </template>
        </dl>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/accept'
// 列表状态落在 localStorage：关掉详情、切去别的模块甚至隔天再打开，都停在原来那一页
const STATE_KEY = 'accept-list-state'
const columns = ["验收单号", "关联施工", "验收项目", "验收标准", "验收结论", "验收人员", "验收日期", "验收状态"]
const actions = ["开始验收", "确认通过", "下发返工", "作废验收"]
const statuses = ["待验收", "验收中", "已通过", "需返工"]
const sizeOptions = [10, 20, 50, 100]
const stats = [{"label": "待验收单据", "value": 0}, {"label": "本月通过数", "value": 0}, {"label": "需返工项数", "value": 0}]

interface ListState {
  page: number
  size: number
  keyword: string
  status: string
}

function loadState(): ListState {
  const fallback: ListState = { page: 1, size: 20, keyword: '', status: '' }
  try {
    const raw = window.localStorage.getItem(STATE_KEY)
    if (!raw) {
      return fallback
    }
    const parsed = JSON.parse(raw) as Partial<ListState>
    const page = Math.floor(Number(parsed.page))
    const size = Number(parsed.size)
    return {
      page: Number.isInteger(page) && page > 0 ? page : fallback.page,
      size: sizeOptions.includes(size) ? size : fallback.size,
      keyword: typeof parsed.keyword === 'string' ? parsed.keyword : '',
      status: typeof parsed.status === 'string' ? parsed.status : '',
    }
  } catch {
    return fallback
  }
}

const saved = loadState()
const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(saved.page)
const size = ref(saved.size)
const filters = ref({ keyword: saved.keyword, status: saved.status })
const jumpTarget = ref<number | null>(null)
const errorMessage = ref('')
const noticeMessage = ref('')
const detail = ref<Row | null>(null)

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

function saveState() {
  window.localStorage.setItem(STATE_KEY, JSON.stringify({
    page: page.value,
    size: size.value,
    keyword: filters.value.keyword,
    status: filters.value.status,
  }))
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (filters.value.keyword.trim()) {
    query.set('keyword', filters.value.keyword.trim())
  }
  if (filters.value.status) {
    query.set('status', filters.value.status)
  }
  query.set('page', String(page.value))
  query.set('size', String(size.value))
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error('验收单列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    // 页码越界时后端会先校验再钳到合法页，这里以返回的页码为准并记住
    if (Number.isInteger(payload.page) && payload.page !== page.value) {
      page.value = payload.page
    }
    noticeMessage.value = payload.notice ?? ''
    saveState()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '竣工验收列表读取失败'
  }
}

function goPage(target: number) {
  // 翻页只动页码，筛选条件保持不动
  page.value = target
  void reload()
}

function changeSize() {
  // 改了每页条数就从第一页重新翻，已看过的单据不重复也不漏掉
  page.value = 1
  void reload()
}

function jumpToPage() {
  const target = Number(jumpTarget.value)
  jumpTarget.value = null
  if (!Number.isInteger(target)) {
    noticeMessage.value = '跳转页码需要是整数'
    return
  }
  // 越界页码交给后端校验：会落到合法页并说明是哪一头不合法
  page.value = target
  void reload()
}

function applyFilters() {
  page.value = 1
  void reload()
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  page.value = 1
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
      throw new Error('验收单明细读取失败')
    }
    detail.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '验收单明细读取失败'
  }
}

function closeDetail() {
  // 只关面板，列表的页码与条件原样保留
  detail.value = null
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('竣工验收动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '竣工验收操作失败'
  }
}

onMounted(reload)
</script>
