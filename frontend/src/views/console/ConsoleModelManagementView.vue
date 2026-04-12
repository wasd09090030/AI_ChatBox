<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import ConfigPageHeader from '@/components/config/ConfigPageHeader.vue'
import ConfigResetPanel from '@/components/config/ConfigResetPanel.vue'
import GenerationParamsPanel from '@/components/config/GenerationParamsPanel.vue'
import ProviderConfigCards from '@/components/config/ProviderConfigCards.vue'
import { Separator } from '@/components/ui/separator'
import { useDashboardConfig } from '@/domains/settings/composables/useDashboardConfig'

const {
  configStore,
  currentToneInfo,
  effectiveTemp,
  currentWorldName,
  PROVIDERS,
  keyInputs,
  baseUrlInputs,
  showKey,
  showAdvanced,
  saving,
  testing,
  testResults,
  fetchingModels,
  remoteModels,
  selectedModels,
  persistSelectedModels,
  keyStatus,
  modelsForProvider,
  setAsDefault,
  isDefaultProvider,
  testConnection,
  fetchModels,
  saveKey,
  deleteKey,
  saveBaseUrl,
  toggleAdvanced,
  tempInput,
  tempError,
  onTempInput,
  maxTokensInput,
  maxTokensError,
  onMaxTokensInput,
  resetConfig,
} = useDashboardConfig()
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <div class="mx-auto max-w-2xl space-y-8 px-6 py-8">
      <ConfigPageHeader />

      <Separator />

      <ProviderConfigCards
        :providers="PROVIDERS"
        :key-inputs="keyInputs"
        :base-url-inputs="baseUrlInputs"
        :show-key="showKey"
        :show-advanced="showAdvanced"
        :saving="saving"
        :testing="testing"
        :test-results="testResults"
        :fetching-models="fetchingModels"
        :remote-models="remoteModels"
        :selected-models="selectedModels"
        :is-default-provider="isDefaultProvider"
        :key-status="keyStatus"
        :models-for-provider="modelsForProvider"
        :persist-selected-models="persistSelectedModels"
        :save-key="saveKey"
        :delete-key="deleteKey"
        :test-connection="testConnection"
        :fetch-models="fetchModels"
        :set-as-default="setAsDefault"
        :toggle-advanced="toggleAdvanced"
        :save-base-url="saveBaseUrl"
      />

      <Separator />

      <GenerationParamsPanel
        :temperature="configStore.config.temperature"
        :max-tokens="configStore.config.maxTokens"
        :temp-input="tempInput"
        :temp-error="tempError"
        :max-tokens-input="maxTokensInput"
        :max-tokens-error="maxTokensError"
        :current-tone-info="currentToneInfo"
        :current-world-name="currentWorldName"
        :effective-temp="effectiveTemp"
        @temp-input="onTempInput"
        @max-tokens-input="onMaxTokensInput"
      />

      <Separator />

      <ConfigResetPanel :on-reset="resetConfig" />
    </div>
  </div>
</template>
