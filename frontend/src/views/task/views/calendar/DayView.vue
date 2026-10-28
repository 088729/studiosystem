<template>
  <TimeGrid :days="days" :tasks="tasks" :focus-sessions="focusSessions" @open="$emit('open', $event)" @create="$emit('create', $event)" @reschedule="(t, d, m) => $emit('reschedule', t, d, m)" />
</template>

<script setup>
import { computed } from 'vue'
import TimeGrid from './TimeGrid.vue'

const props = defineProps({ tasks: Array, focusSessions: { type: Array, default: () => [] }, cursor: Object })
defineEmits(['open', 'create', 'reschedule'])

const days = computed(() => [props.cursor.startOf('day')])
</script>
