<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value?: string | null
    items?: Array<string | null | undefined>
    tone?: 'industry' | 'subIndustry' | 'product' | 'customer' | 'stage'
    compact?: boolean
  }>(),
  {
    value: '',
    items: undefined,
    tone: 'industry',
    compact: false,
  },
)

function splitValue(value: string) {
  return value
    .split(/[、,，;；/\n\r]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function audienceChips(value: string) {
  const chips: string[] = []

  if (/女/.test(value)) chips.push('女性')
  if (/男/.test(value)) chips.push('男性')

  ;['一线', '二线', '三线', '四线'].forEach((tier) => {
    if (value.includes(tier)) chips.push(`${tier}城市`)
  })

  const interestMatch = value.match(/(?:兴趣|爱好|喜欢|偏好)[:：]?\s*([^，,。；;\n]+)/)
  if (interestMatch?.[1]) {
    chips.push(`兴趣 ${interestMatch[1].trim().slice(0, 14)}`)
  }

  splitValue(value).forEach((item) => {
    if (!chips.some((chip) => chip.includes(item) || item.includes(chip))) {
      chips.push(item)
    }
  })

  return chips
}

const chips = computed(() => {
  const source: string[] = props.items?.length
    ? props.items.map((item) => item?.trim()).filter((item): item is string => Boolean(item))
    : props.tone === 'customer'
      ? audienceChips(props.value ?? '')
      : splitValue(props.value ?? '')

  return source.length ? source.slice(0, props.compact ? 4 : 8) : ['未填写']
})
</script>

<template>
  <div :class="['field-chip-group', `field-chip-group-${tone}`, { compact }]">
    <span class="field-chip-label">{{ label }}</span>
    <div class="field-chip-row">
      <span v-for="chip in chips" :key="chip" class="field-chip">{{ chip }}</span>
    </div>
  </div>
</template>
