// 布局结构图片映射（参考 simple-mind-map 官方 demo）
import logicalStructure from '@/assets/img/structures/logicalStructure.jpg'
import logicalStructureLeft from '@/assets/img/structures/logicalStructureLeft.jpg'
import mindMap from '@/assets/img/structures/mindMap.jpg'
import organizationStructure from '@/assets/img/structures/organizationStructure.jpg'
import catalogOrganization from '@/assets/img/structures/catalogOrganization.jpg'
import timeline from '@/assets/img/structures/timeline.jpg'
import timeline2 from '@/assets/img/structures/timeline2.jpg'
import fishbone from '@/assets/img/structures/fishbone.jpg'
import verticalTimeline from '@/assets/img/structures/verticalTimeline.jpg'

export const layoutImgMap = {
  logicalStructure,
  logicalStructureLeft,
  mindMap,
  organizationStructure,
  catalogOrganization,
  timeline,
  timeline2,
  fishbone,
  verticalTimeline,
}

// 布局分组（与官方 demo 一致，不含向右鱼骨图）
export const layoutGroupList = [
  {
    name: '逻辑结构图',
    list: ['logicalStructure', 'logicalStructureLeft'],
  },
  {
    name: '思维导图',
    list: ['mindMap'],
  },
  {
    name: '组织结构图',
    list: ['organizationStructure'],
  },
  {
    name: '目录组织图',
    list: ['catalogOrganization'],
  },
  {
    name: '时间轴',
    list: ['timeline', 'timeline2', 'verticalTimeline'],
  },
  {
    name: '鱼骨图',
    list: ['fishbone'],
  },
]
