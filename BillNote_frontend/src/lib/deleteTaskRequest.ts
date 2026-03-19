export interface DeleteTaskPayload {
  task_id?: string
  video_id?: string
  platform: string
}

export const buildDeleteTaskPayload = ({ task_id, video_id, platform }: DeleteTaskPayload) => {
  const payload: DeleteTaskPayload = { platform }

  if (task_id) {
    payload.task_id = task_id
  }

  if (video_id) {
    payload.video_id = video_id
  }

  return payload
}
