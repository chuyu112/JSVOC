<script setup lang="ts">
const model = defineModel<string>({ default: '' })

const productOptions = [
  { label: '手镯', icon: '镯', tone: 'bracelet' },
  { label: '挂件', icon: '挂', tone: 'pendant' },
  { label: '材料', icon: '料', tone: 'material' },
  { label: '镶嵌', icon: '嵌', tone: 'inlay' },
  { label: '戒面', icon: '戒', tone: 'cabochon' },
  { label: '珠串', icon: '珠', tone: 'beads' },
]

function splitProducts(value: string) {
  return value
    .split(/[、,，;；/\n\r]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function selectedProducts() {
  return splitProducts(model.value)
}

function isSelected(label: string) {
  return selectedProducts().includes(label)
}

function toggleProduct(label: string) {
  const current = selectedProducts()
  const next = current.includes(label)
    ? current.filter((item) => item !== label)
    : [...current, label]

  model.value = next.join('、')
}
</script>

<template>
  <div class="product-multiselect">
    <div class="product-option-grid" aria-label="产品类型">
      <button
        v-for="option in productOptions"
        :key="option.label"
        type="button"
        :class="[
          'product-option',
          `product-option-${option.tone}`,
          { 'is-selected': isSelected(option.label) },
        ]"
        @click="toggleProduct(option.label)"
      >
        <span class="product-option-icon" :data-icon="option.icon"></span>
        <span class="product-option-label">{{ option.label }}</span>
      </button>
    </div>
    <el-input v-model="model" placeholder="也可以直接输入：手镯、挂件、材料、镶嵌" />
  </div>
</template>
