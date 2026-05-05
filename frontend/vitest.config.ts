import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const runtime = globalThis as { process?: { env?: { CI?: string } } };

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    // CI=true のとき JUnit レポーターを有効化（azure-pipelines.yml PublishTestResults 用）
    reporters: runtime.process?.env?.CI ? ['verbose', 'junit'] : ['verbose'],
    outputFile: {
      junit: '../test-results/vitest.xml',
    },
  },
});
