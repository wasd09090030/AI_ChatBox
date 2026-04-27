<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, BookOpen, KeyRound, ScrollText, Sparkles } from 'lucide-vue-next'
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
const featureHighlights = [
  {
    title: '世界设定',
    description: '在同一个工作台里管理世界书、角色与关键事件，让设定先于生成成型。',
    icon: BookOpen,
  },
  {
    title: '双创作模式',
    description: '支持渐进式创作和剧本主导创作，两种推进方式围绕同一条故事链路协作。',
    icon: ScrollText,
  },
  {
    title: '记忆与调整',
    description: '故事分支、上下文编排和文本调整围绕运行态协同，而不是散落成几个孤立页面。',
    icon: Sparkles,
  },
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
  <div class="login-shell min-h-screen overflow-hidden bg-background text-foreground">
    <div class="login-shell__grid" aria-hidden="true" />
    <div class="relative mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
      <div class="grid flex-1 gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(24rem,30rem)]">
        <section
          class="login-panel relative overflow-hidden rounded-[2rem] border border-border/70 bg-card/95 px-6 py-8 shadow-[0_30px_120px_rgba(15,23,42,0.08)] backdrop-blur xl:px-10 xl:py-10"
        >
          <div class="login-orb login-orb-primary" aria-hidden="true" />
          <div class="login-orb login-orb-accent" aria-hidden="true" />
          <div class="login-divider absolute inset-x-10 top-0 h-px" aria-hidden="true" />

          <div class="relative flex h-full flex-col justify-center gap-8">
            <div class="space-y-7">
              <div
                class="inline-flex w-fit items-center gap-3 rounded-full border border-border/80 bg-background/85 px-3 py-2 text-xs uppercase tracking-[0.3em] text-muted-foreground shadow-sm"
              >
                <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  <BookOpen class="h-4 w-4" />
                </span>
                Story Workshop
              </div>

              <div class="max-w-3xl space-y-4">
                <p class="text-sm uppercase tracking-[0.32em] text-muted-foreground">
                  Story Design Workspace
                </p>
                <h1 class="max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
                  从世界设定到剧情推进，
                  <span class="text-primary">都在同一个故事工作台里完成。</span>
                </h1>
                <p class="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
                  这个项目聚焦故事设计与生成，不把世界观、角色、剧本、记忆和正文创作拆成互不相干的工具。
                  登录页只保留这条主线，不再堆实现细节。
                </p>
              </div>

              <div class="space-y-3">
                <p class="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                  特色功能
                </p>
                <div class="grid gap-4 md:grid-cols-3">
                  <article
                    v-for="item in featureHighlights"
                    :key="item.title"
                    class="rounded-[1.5rem] border border-border/70 bg-background/80 p-5 shadow-[0_14px_40px_rgba(15,23,42,0.05)] backdrop-blur"
                  >
                    <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                      <component :is="item.icon" class="h-5 w-5" />
                    </div>
                    <h3 class="mt-4 text-base font-semibold tracking-tight">{{ item.title }}</h3>
                    <p class="mt-2 text-sm leading-6 text-muted-foreground">
                      {{ item.description }}
                    </p>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="flex w-full items-stretch">
          <div
            class="login-panel login-panel-secondary relative w-full overflow-hidden rounded-[2rem] border border-border/70 bg-card/95 px-6 py-8 shadow-[0_24px_80px_rgba(15,23,42,0.09)] backdrop-blur sm:px-8"
          >
            <div class="login-divider absolute inset-x-8 top-0 h-px" aria-hidden="true" />

            <div class="mb-8 flex items-start justify-between gap-4">
              <div class="space-y-2">
                <p class="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                  Account Access
                </p>
                <h2 class="text-3xl font-semibold tracking-tight">
                  {{ isRegisterMode ? '创建你的工作区身份' : '回到故事工坊' }}
                </h2>
                <p class="text-sm leading-6 text-muted-foreground">
                  使用账号进入当前工作区，恢复属于这个用户的会话、配置和故事状态。
                </p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl border border-border/80 bg-background/85 text-primary shadow-sm">
                <KeyRound class="h-5 w-5" />
              </div>
            </div>

            <div class="mb-6 grid grid-cols-2 rounded-2xl border border-border/80 bg-muted/55 p-1.5">
              <button
                type="button"
                class="rounded-[0.95rem] px-4 py-2.5 text-sm font-medium transition"
                :class="mode === 'login' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                @click="mode = 'login'"
              >
                登录
              </button>
              <button
                type="button"
                class="rounded-[0.95rem] px-4 py-2.5 text-sm font-medium transition"
                :class="mode === 'register' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                @click="mode = 'register'"
              >
                注册
              </button>
            </div>

            <form class="space-y-5" @submit.prevent="handleSubmit">
              <div v-if="isRegisterMode" class="space-y-2">
                <Label for="display-name" class="text-sm font-medium text-foreground">显示名称</Label>
                <Input
                  id="display-name"
                  v-model="displayName"
                  placeholder="例如：夜航校稿人"
                  class="h-12 rounded-xl border-border/80 bg-background/80 shadow-none focus-visible:ring-2 focus-visible:ring-primary/15"
                  maxlength="64"
                />
              </div>

              <div class="space-y-2">
                <Label for="login-identifier" class="text-sm font-medium text-foreground">登录标识</Label>
                <Input
                  id="login-identifier"
                  v-model="loginIdentifier"
                  autocomplete="username"
                  placeholder="邮箱、用户名或内部代号"
                  class="h-12 rounded-xl border-border/80 bg-background/80 shadow-none focus-visible:ring-2 focus-visible:ring-primary/15"
                  minlength="3"
                  maxlength="128"
                  required
                />
              </div>

              <div class="space-y-2">
                <Label for="password" class="text-sm font-medium text-foreground">密码</Label>
                <Input
                  id="password"
                  v-model="password"
                  type="password"
                  autocomplete="current-password"
                  placeholder="至少 8 位"
                  class="h-12 rounded-xl border-border/80 bg-background/80 shadow-none focus-visible:ring-2 focus-visible:ring-primary/15"
                  minlength="8"
                  maxlength="256"
                  required
                />
              </div>

              <div
                v-if="legacyUserId"
                class="rounded-[1.25rem] border border-sky-200/80 bg-sky-50/85 px-4 py-3 text-sm leading-6 text-sky-950"
              >
                检测到旧匿名标识 <span class="font-medium">{{ legacyUserId }}</span>。
                登录后会尝试认领可安全迁移的旧数据；当前阶段后端仍采用保守迁移策略。
              </div>

              <div
                v-if="submitError || authStore.lastError"
                class="rounded-[1.25rem] border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive"
              >
                {{ submitError || authStore.lastError }}
              </div>

              <Button
                type="submit"
                class="h-12 w-full rounded-xl text-sm"
                :disabled="authStore.isBusy"
              >
                <ArrowRight class="h-4 w-4" />
                {{ authStore.isBusy ? '处理中…' : isRegisterMode ? '注册并进入工作台' : '登录并继续创作' }}
              </Button>
            </form>

            <div class="mt-6 rounded-[1.5rem] border border-border/70 bg-muted/35 p-4">
              <p class="text-sm leading-6 text-muted-foreground">
                认证成功后会恢复你的会话，并只加载当前账号名下的配置、分支树和远端持久化状态。
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-shell {
  position: relative;
  isolation: isolate;
  background:
    radial-gradient(circle at 8% 12%, hsl(var(--primary) / 0.05), transparent 24%),
    radial-gradient(circle at 88% 14%, rgba(14, 165, 233, 0.12), transparent 24%),
    linear-gradient(180deg, hsl(var(--background)) 0%, hsl(var(--secondary) / 0.72) 100%);
}

.login-shell__grid {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.75;
  background-image:
    linear-gradient(to right, hsl(var(--border) / 0.38) 1px, transparent 1px),
    linear-gradient(to bottom, hsl(var(--border) / 0.22) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: radial-gradient(circle at center, black 38%, transparent 100%);
}

.login-panel {
  animation: login-rise 0.72s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.login-panel-secondary {
  animation-delay: 0.08s;
}

.login-divider {
  background: linear-gradient(90deg, transparent, hsl(var(--border) / 0.9), transparent);
}

.login-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(32px);
  opacity: 0.75;
  animation: login-drift 18s ease-in-out infinite;
}

.login-orb-primary {
  top: -5rem;
  right: 8%;
  width: 15rem;
  height: 15rem;
  background: radial-gradient(circle, hsl(var(--primary) / 0.14), transparent 68%);
}

.login-orb-accent {
  bottom: -7rem;
  left: -4rem;
  width: 18rem;
  height: 18rem;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.18), transparent 72%);
  animation-delay: -7s;
}

@keyframes login-rise {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.985);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes login-drift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }

  50% {
    transform: translate3d(0, 18px, 0) scale(1.04);
  }
}
</style>
