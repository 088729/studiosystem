// 习惯图标库（对齐主流待办应用习惯图标）：Noto Color Emoji 本地 vendor
// key 存到后端 habit.icon，habitIconOf 兜底 smile
import smile from '@/assets/habit-icons/smile.svg'
import book from '@/assets/habit-icons/book.svg'
import run from '@/assets/habit-icons/run.svg'
import water from '@/assets/habit-icons/water.svg'
import fruit from '@/assets/habit-icons/fruit.svg'
import music from '@/assets/habit-icons/music.svg'
import pen from '@/assets/habit-icons/pen.svg'
import gym from '@/assets/habit-icons/gym.svg'
import sleep from '@/assets/habit-icons/sleep.svg'
import coffee from '@/assets/habit-icons/coffee.svg'
import laptop from '@/assets/habit-icons/laptop.svg'
import lotus from '@/assets/habit-icons/lotus.svg'
import bike from '@/assets/habit-icons/bike.svg'
import walk from '@/assets/habit-icons/walk.svg'
import broom from '@/assets/habit-icons/broom.svg'
import grad from '@/assets/habit-icons/grad.svg'
import heart from '@/assets/habit-icons/heart.svg'
import memo from '@/assets/habit-icons/memo.svg'
import seedling from '@/assets/habit-icons/seedling.svg'

export const HABIT_ICONS = [
  { key: 'smile', src: smile, label: '微笑' },
  { key: 'book', src: book, label: '阅读' },
  { key: 'run', src: run, label: '跑步' },
  { key: 'water', src: water, label: '喝水' },
  { key: 'fruit', src: fruit, label: '水果' },
  { key: 'music', src: music, label: '音乐' },
  { key: 'pen', src: pen, label: '写作' },
  { key: 'gym', src: gym, label: '健身' },
  { key: 'sleep', src: sleep, label: '睡觉' },
  { key: 'coffee', src: coffee, label: '咖啡' },
  { key: 'laptop', src: laptop, label: '工作' },
  { key: 'lotus', src: lotus, label: '冥想' },
  { key: 'bike', src: bike, label: '骑行' },
  { key: 'walk', src: walk, label: '散步' },
  { key: 'broom', src: broom, label: '打扫' },
  { key: 'grad', src: grad, label: '学习' },
  { key: 'heart', src: heart, label: '健康' },
  { key: 'memo', src: memo, label: '记录' },
  { key: 'seedling', src: seedling, label: '成长' },
]

const MAP = Object.fromEntries(HABIT_ICONS.map((i) => [i.key, i.src]))

export function habitIconOf(key) {
  return MAP[key] || smile
}
