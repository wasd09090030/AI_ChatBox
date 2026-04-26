<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpenText, Feather, KeyRound, ScrollText, ShieldCheck } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuthStore } from '@/stores/auth'
import { clearLegacyUserId } from '@/domains/user/api/userIdentity'

type AuthMode = 'login' | 'register'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const mode = ref<AuthMode>('login')
const loginIdentifier = ref('')
const password = ref('')
const displayName = ref('')
const submitError = ref<string | null>(null)

const isRegisterMode = computed(() => mode.value === 'register')
const legacyUserId = computed(() => authStore.legacyUserId)
const authHighlights = [
  '账号密码登录，浏览器仅保存 HttpOnly 会话 Cookie。',
  '故事、世界、Lorebook 与运行时状态按用户隔离。',
  '同设备切换账号时，本地缓存也按用户命名空间切分。',
]

function resolveRedirectTarget() {
  const redirect = route.query.redirect
  if (typeof redirect !== 'string') {
    return '/story/improv'
  }
  return redirect.startsWith('/') ? redirect : '/story/improv'
}

async function handleSubmit() {
  submitError.value = null
  authStore.clearError()

  try {
    if (isRegisterMode.value) {
      await authStore.register({
        login_identifier: loginIdentifier.value.trim(),
        password: password.value,
        display_name: displayName.value.trim() || undefined,
      })
    } else {
      await authStore.login({
        login_identifier: loginIdentifier.value.trim(),
        password: password.value,
      })
    }

    if (legacyUserId.value) {
      try {
        const result = await authStore.claimLegacyData()
        if (result?.success) {
          clearLegacyUserId()
        }
      } catch {
        // Claim is non-blocking while the backend migration path is still conservative.
      }
    }

    await router.replace(resolveRedirectTarget())
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : '认证失败，请稍后重试。'
  }
}
</script>

<template>
  <div class="login-shell min-h-screen overflow-hidden text-[var(--ink-strong)]">
    <div class="login-grain" aria-hidden="true" />
    <div class="relative mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-5 sm:px-6 lg:flex-row lg:px-8">
      <section
        class="relative flex flex-1 overflow-hidden rounded-[2rem] border border-[var(--paper-edge)] bg-[var(--paper-soft)]/90 px-6 py-8 shadow-[0_30px_120px_rgba(82,56,31,0.16)] backdrop-blur md:px-10 lg:mr-5 lg:min-h-[calc(100vh-2.5rem)] lg:px-12 lg:py-12"
      >
        <div class="login-ornament login-ornament-left" aria-hidden="true" />
        <div class="login-ornament login-ornament-right" aria-hidden="true" />

        <div class="relative flex w-full flex-col justify-between gap-8">
          <div class="space-y-6">
            <div
              class="inline-flex w-fit items-center gap-2 rounded-full border border-[var(--paper-edge)] bg-white/70 px-4 py-2 text-[11px] uppercase tracking-[0.32em] text-[var(--ink-muted)]"
            >
              <Feather class="h-3.5 w-3.5 text-[var(--accent-strong)]" />
              Story Workshop Ledger
            </div>

            <div class="max-w-2xl space-y-4">
              <p class="text-sm uppercase tracking-[0.36em] text-[var(--ink-muted)]">
                编辑台已上锁
              </p>
              <h1 class="font-[var(--display-font)] text-4xl leading-tight sm:text-5xl lg:text-6xl">
                把你的世界观、角色设定和创作现场，
                <span class="text-[var(--accent-strong)]">收回到自己的手稿页</span>
              </h1>
              <p class="max-w-xl text-base leading-7 text-[var(--ink-soft)] sm:text-lg">
                这次改造不是表面上的登录弹窗，而是把会话、配置、故事运行态和本地缓存都绑回真实用户。
                伪造请求头不再能跨账号串数据。
              </p>
            </div>

            <div class="grid gap-4 md:grid-cols-3">
              <article
                v-for="item in authHighlights"
                :key="item"
                class="rounded-[1.4rem] border border-[var(--paper-edge)] bg-white/65 p-4"
              >
                <div class="mb-3 h-px w-10 bg-[var(--accent-soft)]" />
                <p class="text-sm leading-6 text-[var(--ink-soft)]">
                  {{ item }}
                </p>
              </article>
            </div>
          </div>

          <div class="grid gap-4 rounded-[1.8rem] border border-dashed border-[var(--accent-soft)] bg-[var(--paper)]/80 p-5 md:grid-cols-3">
            <div class="space-y-2">
              <BookOpenText class="h-5 w-5 text-[var(--accent-strong)]" />
              <p class="font-[var(--body-font)] text-sm uppercase tracking-[0.2em] text-[var(--ink-muted)]">
                世界
              </p>
              <p class="text-sm leading-6 text-[var(--ink-soft)]">
                世界书、事件线、人物档案不再全局共享。
              </p>
            </div>
            <div class="space-y-2">
              <ScrollText class="h-5 w-5 text-[var(--accent-strong)]" />
              <p class="font-[var(--body-font)] text-sm uppercase tracking-[0.2em] text-[var(--ink-muted)]">
                运行态
              </p>
              <p class="text-sm leading-6 text-[var(--ink-soft)]">
                会话、摘要记忆和故事分支树都跟随当前用户。
              </p>
            </div>
            <div class="space-y-2">
              <ShieldCheck class="h-5 w-5 text-[var(--accent-strong)]" />
              <p class="font-[var(--body-font)] text-sm uppercase tracking-[0.2em] text-[var(--ink-muted)]">
                凭证
              </p>
              <p class="text-sm leading-6 text-[var(--ink-soft)]">
                浏览器脚本拿不到会话 Cookie，降低前端侧身份暴露面。
              </p>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-5 flex w-full items-stretch lg:mt-0 lg:max-w-[30rem]">
        <div
          class="relative w-full overflow-hidden rounded-[2rem] border border-[var(--paper-edge)] bg-[rgba(255,251,244,0.92)] px-6 py-8 shadow-[0_24px_80px_rgba(74,51,30,0.14)] backdrop-blur sm:px-8"
        >
          <div class="absolute inset-x-8 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(137,72,44,0.5),transparent)]" />

          <div class="mb-7 flex items-start justify-between gap-4">
            <div>
              <p class="text-xs uppercase tracking-[0.3em] text-[var(--ink-muted)]">
                Account Access
              </p>
              <h2 class="mt-2 font-[var(--display-font)] text-3xl">
                {{ isRegisterMode ? '开一页新手稿' : '回到编辑台' }}
              </h2>
            </div>
            <div class="rounded-full border border-[var(--paper-edge)] bg-white/70 p-3 text-[var(--accent-strong)]">
              <KeyRound class="h-5 w-5" />
            </div>
          </div>

          <div class="mb-6 grid grid-cols-2 rounded-full border border-[var(--paper-edge)] bg-white/75 p-1">
            <button
              type="button"
              class="rounded-full px-4 py-2.5 text-sm transition"
              :class="mode === 'login' ? 'bg-[var(--ink-strong)] text-[var(--paper)] shadow-sm' : 'text-[var(--ink-soft)]'"
              @click="mode = 'login'"
            >
              登录
            </button>
            <button
              type="button"
              class="rounded-full px-4 py-2.5 text-sm transition"
              :class="mode === 'register' ? 'bg-[var(--ink-strong)] text-[var(--paper)] shadow-sm' : 'text-[var(--ink-soft)]'"
              @click="mode = 'register'"
            >
              注册
            </button>
          </div>

          <form class="space-y-5" @submit.prevent="handleSubmit">
            <div v-if="isRegisterMode" class="space-y-2">
              <Label for="display-name" class="text-[var(--ink-soft)]">显示名称</Label>
              <Input
                id="display-name"
                v-model="displayName"
                placeholder="例如：夜航校稿人"
                class="h-12 border-[var(--paper-edge)] bg-white/80"
                maxlength="64"
              />
            </div>

            <div class="space-y-2">
              <Label for="login-identifier" class="text-[var(--ink-soft)]">登录标识</Label>
              <Input
                id="login-identifier"
                v-model="loginIdentifier"
                autocomplete="username"
                placeholder="邮箱、用户名或内部代号"
                class="h-12 border-[var(--paper-edge)] bg-white/80"
                minlength="3"
                maxlength="128"
                required
              />
            </div>

            <div class="space-y-2">
              <Label for="password" class="text-[var(--ink-soft)]">密码</Label>
              <Input
                id="password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                placeholder="至少 8 位"
                class="h-12 border-[var(--paper-edge)] bg-white/80"
                minlength="8"
                maxlength="256"
                required
              />
            </div>

            <div
              v-if="legacyUserId"
              class="rounded-[1.25rem] border border-dashed border-[var(--accent-soft)] bg-[rgba(180,125,85,0.08)] px-4 py-3 text-sm leading-6 text-[var(--ink-soft)]"
            >
              检测到旧匿名标识 <span class="font-medium text-[var(--ink-strong)]">{{ legacyUserId }}</span>。
              登录后会尝试认领可安全迁移的旧数据；当前阶段后端仍采用保守迁移策略。
            </div>

            <div
              v-if="submitError || authStore.lastError"
              class="rounded-[1.25rem] border border-[rgba(167,64,38,0.22)] bg-[rgba(167,64,38,0.08)] px-4 py-3 text-sm text-[rgb(125,47,28)]"
            >
              {{ submitError || authStore.lastError }}
            </div>

            <Button
              type="submit"
              class="h-12 w-full rounded-full bg-[var(--ink-strong)] text-[var(--paper)] transition hover:bg-[var(--ink-soft)]"
              :disabled="authStore.isBusy"
            >
              {{ authStore.isBusy ? '处理中…' : isRegisterMode ? '注册并进入工作台' : '登录并继续创作' }}
            </Button>
          </form>

          <p class="mt-6 text-sm leading-6 text-[var(--ink-muted)]">
            认证成功后会恢复你的会话，并只加载当前账号名下的配置、分支树和远端持久化状态。
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-shell {
  --paper: #f6efe4;
  --paper-soft: #efe4d4;
  --paper-edge: rgba(90, 67, 46, 0.18);
  --ink-strong: #241915;
  --ink-soft: #5b4738;
  --ink-muted: #8b725d;
  --accent-strong: #8f4e31;
  --accent-soft: rgba(143, 78, 49, 0.32);
  --display-font: "Palatino Linotype", "Book Antiqua", "STSong", serif;
  --body-font: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
  background:
    radial-gradient(circle at 15% 20%, rgba(255, 252, 247, 0.86), transparent 30%),
    radial-gradient(circle at 85% 14%, rgba(173, 107, 71, 0.13), transparent 24%),
    linear-gradient(135deg, #d9c3a5 0%, #f4ece0 42%, #d7bea2 100%);
  font-family: var(--body-font);
}

.login-grain {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.24;
  mix-blend-mode: multiply;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.04)),
    radial-gradient(circle at 20% 20%, rgba(95, 70, 48, 0.22) 0.7px, transparent 0.8px);
  background-size: 100% 100%, 12px 12px;
}

.login-ornament {
  position: absolute;
  border-radius: 999px;
  filter: blur(3px);
  opacity: 0.75;
}

.login-ornament-left {
  top: -6rem;
  left: -3rem;
  width: 16rem;
  height: 16rem;
  background: radial-gradient(circle, rgba(166, 111, 76, 0.28), transparent 70%);
}

.login-ornament-right {
  right: -5rem;
  bottom: -6rem;
  width: 18rem;
  height: 18rem;
  background: radial-gradient(circle, rgba(104, 69, 47, 0.16), transparent 72%);
}
</style>
