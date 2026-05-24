import { onMounted, ref, type Ref } from 'vue'
import gsap from 'gsap'

export function useStaggerReveal(
  parentRef: Ref<HTMLElement | null>,
  childSelector = '> *',
  options?: gsap.TweenVars,
) {
  const revealed = ref(false)

  onMounted(() => {
    const parent = parentRef.value
    if (!parent) return

    const children = parent.querySelectorAll(childSelector)
    if (!children.length) return

    gsap.set(children, { opacity: 0, y: 20 })

    gsap.to(children, {
      opacity: 1,
      y: 0,
      duration: 0.6,
      stagger: 0.08,
      ease: 'power3.out',
      delay: 0.1,
      ...options,
    })

    revealed.value = true
  })

  return { revealed }
}
