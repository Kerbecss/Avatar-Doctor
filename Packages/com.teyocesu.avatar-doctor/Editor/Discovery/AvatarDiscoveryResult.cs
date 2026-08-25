using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace Teyocesu.AvatarDoctor.Editor.Discovery
{
    internal sealed class AvatarDiscoveryResult
    {
        internal AvatarDiscoveryResult(
            IEnumerable<AvatarDiscoveryCandidate> candidates)
        {
            if (candidates == null)
            {
                throw new ArgumentNullException(nameof(candidates));
            }

            List<AvatarDiscoveryCandidate> copy =
                new List<AvatarDiscoveryCandidate>();
            foreach (AvatarDiscoveryCandidate candidate in candidates)
            {
                if (candidate == null)
                {
                    throw new ArgumentException(
                        "A discovery result cannot contain a null candidate.",
                        nameof(candidates));
                }

                copy.Add(candidate);
            }

            Candidates = new ReadOnlyCollection<AvatarDiscoveryCandidate>(copy);
            CountState = DeriveCountState(copy.Count);
        }

        internal IReadOnlyList<AvatarDiscoveryCandidate> Candidates { get; }

        internal AvatarDiscoveryState CountState { get; }

        private static AvatarDiscoveryState DeriveCountState(int count)
        {
            if (count == 0)
            {
                return AvatarDiscoveryState.None;
            }

            return count == 1
                ? AvatarDiscoveryState.Single
                : AvatarDiscoveryState.Multiple;
        }
    }
}
