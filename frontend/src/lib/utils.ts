/**
 * 文件说明：项目文件 utils.ts 的核心逻辑实现。
 */

import type { ClassValue } from "clsx"
import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/** 处理 cn 相关逻辑。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
