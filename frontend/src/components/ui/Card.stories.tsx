import type { Meta, StoryObj } from '@storybook/react';
import { Card, CardHeader, CardTitle } from './Card';

const meta = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    padding: {
      control: 'select',
      options: ['none', 'sm', 'md', 'lg'],
    },
  },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: 'Card content goes here',
  },
};

export const WithHeader: Story = {
  args: {
    children: (
      <>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
        </CardHeader>
        <p>Card content with header</p>
      </>
    ),
  },
};

export const SmallPadding: Story = {
  args: {
    padding: 'sm',
    children: 'Card with small padding',
  },
};

export const LargePadding: Story = {
  args: {
    padding: 'lg',
    children: 'Card with large padding',
  },
};

export const NoPadding: Story = {
  args: {
    padding: 'none',
    children: <div className="p-4">Content with custom padding</div>,
  },
};

export const Complex: Story = {
  args: {
    children: (
      <>
        <CardHeader>
          <CardTitle>Product Information</CardTitle>
        </CardHeader>
        <div className="space-y-2">
          <p className="text-sm text-gray-600 dark:text-gray-400">Name: Example Product</p>
          <p className="text-sm text-gray-600 dark:text-gray-400">Price: $29.99</p>
          <p className="text-sm text-gray-600 dark:text-gray-400">Category: Electronics</p>
        </div>
      </>
    ),
  },
};

