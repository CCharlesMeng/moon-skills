/** 批次显示标签：把序号补零成固定 4 位，前置加 `#`。 */
function formatBatchLabel(sequence: number): string {
  return `批次 #${String(sequence).padStart(4, '0')}`;
}

export default formatBatchLabel;
