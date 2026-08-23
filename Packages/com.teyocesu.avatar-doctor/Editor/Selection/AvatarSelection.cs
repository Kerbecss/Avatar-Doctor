using System;
using Teyocesu.AvatarDoctor.Editor.Discovery;

namespace Teyocesu.AvatarDoctor.Editor.Selection
{
    internal sealed class AvatarSelection
    {
        private AvatarSelection(
            AvatarSelectionState state,
            AvatarDiscoveryCandidate candidate,
            AvatarSelectionOrigin? origin)
        {
            State = state;
            Candidate = candidate;
            Origin = origin;
        }

        internal AvatarSelectionState State { get; }

        internal AvatarDiscoveryCandidate Candidate { get; }

        internal AvatarSelectionOrigin? Origin { get; }

        internal static AvatarSelection CreateEmpty()
        {
            return new AvatarSelection(
                AvatarSelectionState.Empty,
                null,
                null);
        }

        internal static AvatarSelection CreateUnresolved()
        {
            return new AvatarSelection(
                AvatarSelectionState.Unresolved,
                null,
                null);
        }

        internal static AvatarSelection CreateSelected(
            AvatarDiscoveryCandidate candidate,
            AvatarSelectionOrigin origin)
        {
            if (candidate == null)
            {
                throw new ArgumentNullException(nameof(candidate));
            }

            return new AvatarSelection(
                AvatarSelectionState.Selected,
                candidate,
                origin);
        }
    }
}
