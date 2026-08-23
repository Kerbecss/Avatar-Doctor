using VRC.SDK3.Avatars.Components;

namespace Teyocesu.AvatarDoctor.Editor.Integrations.VRChat
{
    internal static class VRChatAvatarDescriptorBoundary
    {
        internal static VRCAvatarDescriptor Preserve(
            VRCAvatarDescriptor descriptor)
        {
            return descriptor;
        }
    }
}
