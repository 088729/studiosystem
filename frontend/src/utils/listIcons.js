// 清单图标映射（对齐主流待办应用图标；Lucide currentColor，着色用清单 color）
import {
  Folder, Briefcase, BookOpen, ShoppingCart, Heart, Home, Plane, Dumbbell,
  Music, Code2, Coffee, Star, Flag, Gift, Camera, PenLine, Wallet, Users,
  CalendarDays, Lightbulb,
} from 'lucide-vue-next'

export const LIST_ICONS = [
  { key: 'folder', label: '通用', icon: Folder },
  { key: 'briefcase', label: '工作', icon: Briefcase },
  { key: 'book', label: '学习', icon: BookOpen },
  { key: 'cart', label: '购物', icon: ShoppingCart },
  { key: 'heart', label: '健康', icon: Heart },
  { key: 'home', label: '家庭', icon: Home },
  { key: 'plane', label: '旅行', icon: Plane },
  { key: 'gym', label: '健身', icon: Dumbbell },
  { key: 'music', label: '音乐', icon: Music },
  { key: 'code', label: '开发', icon: Code2 },
  { key: 'coffee', label: '休闲', icon: Coffee },
  { key: 'star', label: '重要', icon: Star },
  { key: 'flag', label: '目标', icon: Flag },
  { key: 'gift', label: '礼物', icon: Gift },
  { key: 'camera', label: '影像', icon: Camera },
  { key: 'pen', label: '创作', icon: PenLine },
  { key: 'wallet', label: '财务', icon: Wallet },
  { key: 'users', label: '人际', icon: Users },
  { key: 'calendar', label: '日程', icon: CalendarDays },
  { key: 'idea', label: '灵感', icon: Lightbulb },
]

// 取清单图标组件；未设置/未知 key 返回 null（调用方回退色点）
export function listIconOf(key) {
  return LIST_ICONS.find((i) => i.key === key)?.icon || null
}
