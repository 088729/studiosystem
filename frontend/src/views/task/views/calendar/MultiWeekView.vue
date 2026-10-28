<template>
  <TimeGrid :days="days" :tasks="tasks" :focus-sessions="focusSessions" @open="$emit('open', $event)" @create="$emit('create', $event)" @reschedule="(t, d, m) => $emit('reschedule', t, d, m)" />
</template>

<script setup>
import { computed } from 'vue'
import TimeGrid from './TimeGrid.vue'

const props = defineProps({ tasks: Array, focusSessions: { type: Array, default: () => [] }, cursor: Object })
defineEmits(['open', 'create', 'reschedule'])

function mondayOf(d) {
  const day = d.day()
  return d.subtract(day === 0 ? 6 : day - 1, 'day').startOf('day')
}

const days = computed(() => {
  const start = mondayOf(props.cursor)
  return Array.from({ length: 14 }, (_, i) => start.add(i, 'day'))
})
</script>
