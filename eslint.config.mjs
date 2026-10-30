import js from '@eslint/js';
import tseslint from 'typescript-eslint';
export default tseslint.config({ ignores: ['reference/**', '**/.next/**', '**/node_modules/**'] }, js.configs.recommended, ...tseslint.configs.recommended);
