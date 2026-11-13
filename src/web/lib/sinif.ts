/** Koşullu sınıf birleştirir; çakışan Tailwind sınıflarında sondaki kazanır. */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...girdi: ClassValue[]): string {
  return twMerge(clsx(girdi));
}