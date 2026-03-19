export interface EnabledModelOption {
  provider_id: string
  model_name: string
}

export const STALE_MODEL_MESSAGE = '当前模型不可用，请刷新模型列表后重试'

export function resolveProviderIdForModel(
  models: EnabledModelOption[],
  modelName: string
): string {
  const match = models.find(model => model.model_name === modelName)

  if (!match?.provider_id) {
    throw new Error(STALE_MODEL_MESSAGE)
  }

  return match.provider_id
}
