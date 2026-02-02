export function formatTime(value: Date) {
  const hours = value.getHours().toString().padStart(2, "0");
  const minutes = value.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}
