import type { Meta, StoryObj } from '@storybook/react';
import { Skeleton } from './Skeleton';

const meta = {
  title: 'UI/Skeleton',
  component: Skeleton,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['text', 'circular', 'rectangular'],
    },
  },
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Text: Story = {
  args: {
    variant: 'text',
    className: 'w-48',
  },
};

export const Circular: Story = {
  args: {
    variant: 'circular',
    className: 'w-12 h-12',
  },
};

export const Rectangular: Story = {
  args: {
    variant: 'rectangular',
    className: 'w-64 h-32',
  },
};

export const MultipleTextLines: Story = {
  render: () => (
    <div className="space-y-2">
      <Skeleton variant="text" className="w-full" />
      <Skeleton variant="text" className="w-5/6" />
      <Skeleton variant="text" className="w-4/6" />
    </div>
  ),
};

export const CardSkeleton: Story = {
  render: () => (
    <div className="w-64 space-y-4 p-4 border rounded-lg">
      <Skeleton variant="circular" className="w-12 h-12" />
      <Skeleton variant="text" className="w-full" />
      <Skeleton variant="text" className="w-3/4" />
      <Skeleton variant="rectangular" className="w-full h-32" />
    </div>
  ),
};

