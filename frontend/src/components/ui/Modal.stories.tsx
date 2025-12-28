import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { useState } from 'react';
import { Modal } from './Modal';
import { Button } from './Button';

const meta = {
  title: 'UI/Modal',
  component: Modal,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg', 'xl'],
    },
  },
  args: { isOpen: false, onClose: fn() },
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

const ModalWrapper = ({ isOpen: initialOpen = false, ...args }: { isOpen?: boolean } & Story['args']) => {
  const [isOpen, setIsOpen] = useState(initialOpen);

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Open Modal</Button>
      <Modal {...args} isOpen={isOpen} onClose={() => setIsOpen(false)}>
        {args?.children || 'Modal content goes here'}
      </Modal>
    </>
  );
};

export const Default: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    title: 'Modal Title',
    children: 'This is the modal content. You can put anything here.',
  },
};

export const WithoutTitle: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    children: 'Modal without a title',
  },
};

export const Small: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    size: 'sm',
    title: 'Small Modal',
    children: 'This is a small modal',
  },
};

export const Large: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    size: 'lg',
    title: 'Large Modal',
    children: 'This is a large modal with more space for content.',
  },
};

export const ExtraLarge: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    size: 'xl',
    title: 'Extra Large Modal',
    children: 'This is an extra large modal for complex content.',
  },
};

export const WithForm: Story = {
  render: (args) => <ModalWrapper {...args} />,
  args: {
    title: 'Form Modal',
    children: (
      <form onSubmit={(e) => e.preventDefault()}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              className="w-full px-3 py-2 border rounded-md"
              placeholder="Enter name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              className="w-full px-3 py-2 border rounded-md"
              placeholder="Enter email"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => { }}>Cancel</Button>
            <Button onClick={() => { }}>Submit</Button>
          </div>
        </div>
      </form>
    ),
  },
};

