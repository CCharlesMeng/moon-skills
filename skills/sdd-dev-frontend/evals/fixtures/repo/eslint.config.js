export default [
  {
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      'no-console': 'error',
      'no-restricted-globals': ['error', { name: 'fetch', message: '请走 src/lib/request.ts' }],
    },
  },
];
