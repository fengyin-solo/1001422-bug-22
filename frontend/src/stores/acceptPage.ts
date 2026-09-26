import { defineStore } from 'pinia'

/**
 * 竣工验收列表的分页与筛选状态。
 *
 * 状态放在 store 而不是组件里：打开详情、跳到别的页面再回来，
 * 列表都停在原来那一页，筛选条件也不会被清空。
 */
export const useAcceptPageStore = defineStore('acceptPage', {
  state: () => ({
    page: 1,
    size: 20,
    keyword: '',
    status: '',
  }),
  actions: {
    gotoPage(page: number) {
      this.page = page
    },
    changeSize(size: number) {
      // 改每页条数后从第一页重新翻，避免旧页码带着旧口径漏单或重复。
      this.size = size
      this.page = 1
    },
    applyFilters(keyword: string, status: string) {
      this.keyword = keyword
      this.status = status
      this.page = 1
    },
    resetFilters() {
      this.keyword = ''
      this.status = ''
      this.page = 1
    },
  },
})
