import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

class POIScaleOptimizer(nn.Module):
    def __init__(self, num_poi_types):
        super().__init__()
        
        # We want to learn the "scale divisor" (e.g. the 800, the 350)
        # We initialize them with your current best guesses to speed up learning
        initial_guesses = torch.tensor([800.0, 600.0, 2500.0, 1200.0, 350.0]) # Add all your types
        
        # We store them as parameters so PyTorch knows to optimize them
        self.raw_scales = nn.Parameter(initial_guesses)
        self.weights = nn.Parameter(torch.ones(num_poi_types))
        
        # A simple base bias (average price change)
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, distance_arrays, masks):
        """
        distance_arrays: Shape (batch_size, num_poi_types, max_pois)
        """
        # Enforce constraints: Scales MUST be positive (Softplus ensures this safely)
        # We add 1.0 to ensure a scale is never mathematically exactly 0
        scales = F.softplus(self.raw_scales) + 1.0 
        
        # Enforce constraints: Weights MUST be positive (Optional, use ReLU)
        w = F.relu(self.weights)
        
        # Reshape for matrix math
        scales = scales.view(1, -1, 1)
        w = w.view(1, -1)
        
        # THE CORE MATH: exp(-distance / scale)
        decay_scores = torch.exp(-distance_arrays / scales)
        
        # Mask out empty padding slots
        decay_scores = decay_scores * masks
        
        # SUM the scores per POI type
        summed_scores = torch.sum(decay_scores, dim=2)
        
        # Multiply by importance weights and sum for final price prediction
        final_prediction = torch.sum(w * summed_scores, dim=1) + self.bias
        
        return final_prediction

# ---- HOW TO EXTRACT YOUR SCALES AFTER TRAINING ----
# optimizer = optim.Adam(model.parameters(), lr=1.0)
# ... run training loop for 50 epochs ...

# Once training is done, print the optimal scales to put into SQL!
print("OPTIMAL SCALES FOR SQL:")
learned_scales = F.softplus(model.raw_scales) + 1.0
print(learned_scales.detach().numpy())
# Output might look like: [642.1, 412.8, 1980.5, 950.2, 210.4]